"""Agent 编排层（doc 16 §七 / doc 43）：意图 → 缺口 → 高风险 → 工具 → 产物 → 记忆 → SSE。

决策动作只有三种：普通回复（chat）/ 调用工具（use_tool）/ 追问用户（ask_user）。
工具只能选注册表内 6 个（真实 handler，见 `agent_skills`），清单外明确「办不了」。
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_logger
from app.evaluations.eval_utils import build_sse_event
from app.models import User
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentStep
from app.services import conversation_service
from app.services._agent_service_core import TOOL_SPECS, agent_core
from app.services.intent_service import OUT_OF_SCOPE_KEYWORDS, intent_classifier
from app.skills.agent_skills import skill_dispatcher

# 下一步建议（doc 16 §7.1 suggestions）
_SUGGESTIONS: dict[str, list[str]] = {
    "jd": ["保存并发布 JD", "生成评分标准"],
    "jd_edit": ["查看 JD", "保存修改"],
    "criteria_edit": ["查看评分标准"],
    "resume_screening": ["上传简历", "查看评估结果"],
    "interview_plan": ["查看面试方案"],
    "resource_delete": ["确认删除"],
    "chat": ["生成 JD", "评估简历", "生成面试方案"],
}


def _chunk_text(text: str, size: int = 24) -> list[str]:
    """按固定步长切块，供 SSE delta 打字机效果。"""
    text = text or ""
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _resp(
    message: str,
    intent: str,
    route: str,
    *,
    steps: list[AgentStep] | None = None,
    artifacts: list[dict] | None = None,
    suggestions: list[str] | None = None,
    requires_confirmation: bool = False,
    missing_fields: list[str] | None = None,
    source: str = "fast",
) -> dict[str, Any]:
    return {
        "message": message,
        "intent": intent,
        "route": route,
        "steps": steps or [],
        "artifacts": artifacts or [],
        "suggestions": suggestions or [],
        "requires_confirmation": requires_confirmation,
        "missing_fields": missing_fields or [],
        "source": source,
    }


def _chat_reply(message: str) -> str:
    """普通回复：清单外明确「办不了」，其余引导能力。"""
    if any(k in (message or "") for k in OUT_OF_SCOPE_KEYWORDS):
        return (
            "抱歉，这个需求目前我还办不了（超出我的能力范围）。"
            "我能帮你：生成 JD、编辑评分标准、评估简历、生成面试方案、删除资源。"
        )
    return "你好，我是 HR Agent。你可以让我生成 JD、评估简历、生成面试方案，或提问企业知识。请问需要我做什么？"


def _missing_reply(intent: str, missing_fields: list[str]) -> str:
    if intent == "jd" and "job_title" in missing_fields:
        return "请先告诉我岗位名称（例如「前端开发工程师」），我再为你生成 JD。"
    if intent == "resource_delete" and "target" in missing_fields:
        return "请指明要删除什么资源（例如「删除前端工程师的 JD」）。"
    return "还缺少必要信息，请补充后我再继续。"


def _tool_reply(intent: str) -> str:
    name = TOOL_SPECS.get(intent, {}).get("name", intent)
    return f"已为你准备「{name}」。"


async def _orchestrate(
    message: str, attachments: list[str], user: User, memory: str, db: AsyncSession
) -> dict[str, Any]:
    """受控编排决策（doc 16 §四/§五 + doc 44）：意图 → 角色 → 缺口 → 工具 → 高风险 → 回复。"""
    result = intent_classifier.classify(message, attachments, memory)
    intent = result["intent"]
    route = result["route"]
    source = result["source"]
    missing_fields = list(result["missing_fields"])

    steps = [AgentStep(id="intent", title="识别意图", status="completed", detail=f"intent={intent}")]

    # 角色 gating（doc 14）：employee 触发招聘/删除工具 → 降级 chat
    if intent != "chat" and not agent_core.check_role(intent, user.role):
        steps.append(AgentStep(id="role", title="权限校验", status="failed", detail="角色无权限"))
        return _resp(
            "抱歉，你的角色没有权限触发该工具。",
            "chat",
            "chat",
            steps=steps,
            source=source,
        )

    # 快通道缺口（doc 16 §4.1）：JD 缺岗位名称 / 删除缺目标，直接追问
    if missing_fields:
        steps.append(AgentStep(id="gap", title="缺口检查", status="completed", detail="缺少必要信息"))
        return _resp(
            _missing_reply(intent, missing_fields),
            intent,
            route,
            steps=steps,
            artifacts=[{"type": "requirements", "intent": intent, "missing_fields": missing_fields}],
            suggestions=_SUGGESTIONS.get(intent, []),
            missing_fields=missing_fields,
            source=source,
        )

    # 调用工具（doc 16 §二 + doc 44：真实执行；前置校验/高风险判定下沉到 handler）
    if intent != "chat" and skill_dispatcher.is_registered(intent):
        outcome = await skill_dispatcher.dispatch(
            intent,
            {"message": message, "attachments": attachments, "memory": memory},
            user,
            db,
        )
        steps.append(
            AgentStep(
                id="tool",
                title=TOOL_SPECS[intent]["name"],
                status="completed",
                detail="执行工具",
                tool=intent,
            )
        )
        steps.extend(outcome.steps)

        # 工具下沉的前置缺口（简历附件 / 编辑目标等）
        if outcome.missing_fields:
            steps.append(AgentStep(id="gap", title="缺口检查", status="completed", detail="缺少必要信息"))
            return _resp(
                outcome.message or _missing_reply(intent, outcome.missing_fields),
                intent,
                route,
                steps=steps,
                artifacts=outcome.artifacts
                or [{"type": "requirements", "intent": intent, "missing_fields": outcome.missing_fields}],
                suggestions=outcome.suggestions or _SUGGESTIONS.get(intent, []),
                missing_fields=outcome.missing_fields,
                source=source,
            )

        # 高风险锁定唯一真源（铁律 #3 / doc 16 §5.2）：TOOL_SPECS 声明 + 未执行完成即强制确认
        requires_confirmation = outcome.requires_confirmation or (
            TOOL_SPECS.get(intent, {}).get("requires_confirmation") and not outcome.executed
        )
        if requires_confirmation:
            steps.append(AgentStep(id="risk", title="高风险校验", status="completed", detail="需二次确认"))
            return _resp(
                outcome.message or f"请确认后执行「{TOOL_SPECS[intent]['name']}」。",
                intent,
                route,
                steps=steps,
                artifacts=outcome.artifacts,
                requires_confirmation=True,
                suggestions=outcome.suggestions or _SUGGESTIONS.get(intent, []),
                source=source,
            )

        return _resp(
            outcome.message or _tool_reply(intent),
            intent,
            route,
            steps=steps,
            artifacts=outcome.artifacts,
            suggestions=outcome.suggestions or _SUGGESTIONS.get(intent, []),
            source=source,
        )

    # 普通回复
    return _resp(
        _chat_reply(message),
        "chat",
        "chat",
        steps=steps,
        suggestions=_SUGGESTIONS["chat"],
        source=source,
    )


async def _resolve_conversation(request: AgentChatRequest, user: User, db: AsyncSession):
    conv = await conversation_service.get_conversation(user, request.conversation_id, db) \
        if request.conversation_id else await conversation_service.create_conversation(
            user, db, title=request.message[:30] or None
        )
    memory = await conversation_service.build_memory(user, conv.id, db)
    return conv, memory


async def _persist(
    conv, request: AgentChatRequest, resp: AgentChatResponse, user: User, db: AsyncSession
) -> None:
    """落库 user/assistant 消息（assistant 的 context 存 agent_response，供指代解析与审计）。"""
    await conversation_service.add_message(db, conv.id, "user", request.message)
    await conversation_service.add_message(
        db,
        conv.id,
        "assistant",
        resp.message,
        context={"agent_response": resp.model_dump(mode="json"), "source": resp.source},
    )
    if resp.intent == "chat":
        return
    # 删除确认执行（delete_resource_result）→ 高风险 executed；否则按确认态/工具调用留痕
    executed = any(
        isinstance(a, dict) and a.get("type") == "delete_resource_result"
        for a in (resp.artifacts or [])
    )
    if executed:
        audit_logger.log_high_risk(
            user_id=user.id,
            username=user.username,
            intent=resp.intent,
            target=resp.intent,
            outcome="executed",
        )
    elif resp.requires_confirmation:
        audit_logger.log_high_risk(
            user_id=user.id,
            username=user.username,
            intent=resp.intent,
            target=resp.intent,
            outcome="pending_confirmation",
        )
    else:
        audit_logger.log_tool_call(
            user_id=user.id,
            username=user.username,
            intent=resp.intent,
            tool=resp.intent,
            success=True,
        )


async def handle_message(
    request: AgentChatRequest, user: User, db: AsyncSession
) -> AgentChatResponse:
    """非流式编排：返回完整 AgentChatResponse（8 契约字段）。"""
    conv, memory = await _resolve_conversation(request, user, db)
    result = await _orchestrate(request.message, request.attachments, user, memory, db)
    resp = AgentChatResponse(**result, conversation_id=conv.id)
    await _persist(conv, request, resp, user, db)
    return resp


async def stream_chat(
    request: AgentChatRequest, user: User, db: AsyncSession
) -> AsyncIterator[str]:
    """对话流式 SSE：thinking → plan → delta → final（doc 16 §7.3）。

    编排/工具/外部服务失败时发 error 事件并终止流，绝不静默断流——否则前端会一直停在
    「正在思考」收不到任何事件。
    """
    try:
        conv, memory = await _resolve_conversation(request, user, db)
        result = await _orchestrate(request.message, request.attachments, user, memory, db)
        resp = AgentChatResponse(**result, conversation_id=conv.id)
        await _persist(conv, request, resp, user, db)
    except Exception as exc:  # noqa: BLE001 —— 统一转为可读 error 事件
        yield build_sse_event("error", {"message": f"处理失败，请重试：{exc}"})
        return

    yield build_sse_event("thinking", {"content": "正在理解你的需求…"})
    yield build_sse_event(
        "plan",
        {"intent": resp.intent, "route": resp.route, "steps": [s.model_dump() for s in resp.steps]},
    )
    for chunk in _chunk_text(resp.message):
        yield build_sse_event("delta", {"content": chunk})
    yield build_sse_event("final", resp.model_dump(mode="json"))


async def stream_agent(
    request: AgentChatRequest, user: User, db: AsyncSession
) -> AsyncIterator[str]:
    """任务型流式 SSE：progress → delta → artifact → final（doc 16 §7.3）。

    编排/工具/外部服务失败时发 error 事件并终止流，绝不静默断流。
    """
    try:
        conv, memory = await _resolve_conversation(request, user, db)
        result = await _orchestrate(request.message, request.attachments, user, memory, db)
        resp = AgentChatResponse(**result, conversation_id=conv.id)
        await _persist(conv, request, resp, user, db)
    except Exception as exc:  # noqa: BLE001 —— 统一转为可读 error 事件
        yield build_sse_event("error", {"message": f"处理失败，请重试：{exc}"})
        return

    yield build_sse_event("progress", {"step": "intent", "detail": f"识别意图: {resp.intent}"})
    for chunk in _chunk_text(resp.message):
        yield build_sse_event("delta", {"content": chunk})
    for artifact in resp.artifacts:
        yield build_sse_event("artifact", {"artifact": artifact})
    yield build_sse_event("final", resp.model_dump(mode="json"))
