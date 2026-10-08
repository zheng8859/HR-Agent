"""Agent 技能分发器（doc 16 §二/§五 + doc 44）：6 工具真实 handler，挂到 43 的注册表。

每个 handler 把「工具专属前置校验 → 业务服务/Dify → 产物」下沉到本模块，返回 `ToolOutcome`
（多产物 + 缺口 + 确认 + 建议 + 步骤）；编排层只做意图/角色/合并。清单外 intent 抛 ValueError。

邮件通知（`hr-agent-email`）/ 试卷生成本期不做，仅保留分发位（doc 44 范围）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ResumeEvaluation, ScoringCriteria, User
from app.schemas.agent import AgentStep
from app.schemas.interview_plan import InterviewPlanGenerateRequest
from app.schemas.job_description import JDGenerateRequest
from app.services import (
    interview_plan_service,
    job_description_service,
    resume_evaluation_service,
    scoring_criteria_service,
)
from app.services._agent_service_core import TOOL_SPECS, agent_core


@dataclass
class ToolOutcome:
    """工具执行结果（doc 44）：多产物 + 缺口 + 确认 + 建议 + 步骤。

    `executed=True` 表示高风险动作已完成（如「确认删除」），编排层不再强制二次确认。
    """

    artifacts: list[dict] = field(default_factory=list)
    message: str | None = None
    missing_fields: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    suggestions: list[str] = field(default_factory=list)
    steps: list[AgentStep] = field(default_factory=list)
    executed: bool = False


# ---------- 目标名称抽取（口语化指令 → 资源/候选人名称） ----------

_CMD_STRIP_RE = re.compile(
    r"^(请|麻烦|帮我|给我|我要|我想|拟|写|生成|创建|做|来|改|修改|编辑|更新|调整|润色|完善|"
    r"删除|删掉|移除|确认|确定|为|给)(一下|一[份个名位]|个|位|名|份)?"
)
_RESOURCE_SUFFIX_RE = re.compile(
    r"(的)?\s*(JD|岗位描述|职位描述|招聘启事|招聘|启事|岗位|职位|评分标准|标准|面试方案|方案)\s*$"
)


def _extract_target(message: str) -> str:
    """从口语化指令抽取资源/候选人名称：循环去句首命令词、截断描述、去资源类型后缀。

    「生成全栈工程师JD，本科，熟悉JAVA,Python…」应只取「全栈工程师」——标题后的逗号（或
    其它标点）分隔的是学历/经验/薪资等描述，须先按首个分隔符截断，再剥离「JD/岗位/职位」
    等资源后缀；否则整句会被当成标题（超过 Dify jobName 的 48 字上限而被 400 拒收）。
    """
    text = (message or "").strip()
    # 反复剥离句首命令词（如「帮我生成一份」「确认删除」），直到句首不再是命令词
    while True:
        m = _CMD_STRIP_RE.match(text)
        if not m:
            break
        text = text[m.end():].strip()
    # 截断标题后的描述段（学历/经验/薪资等，通常用逗号/句号/顿号分隔）
    text = re.split(r"[，,。；;、]", text, maxsplit=1)[0].strip()
    text = _RESOURCE_SUFFIX_RE.sub("", text).strip().strip("，,。；;的 ")
    return text


def _extract_candidate(message: str) -> str:
    """抽取候选人姓名（「为张三生成面试方案」→ 张三）。"""
    text = (message or "").strip()
    while True:
        m = re.match(r"^(请|麻烦|帮我|给我|为|给|想为|想给)", text)
        if not m:
            break
        text = text[m.end():].strip()
    text = re.sub(r"(生成|做|出|来|拟)?\s*(一份|一个|一份|位)?\s*面试方案.*$", "", text).strip()
    return text.strip("，,。；;的 ")


# ---------- 产物简报 ----------


def _jd_brief(jd: Any) -> dict[str, Any]:
    return {"id": str(jd.id), "title": jd.title, "status": jd.status}


def _criteria_brief(sc: Any) -> dict[str, Any]:
    return {"id": str(sc.id), "title": sc.title, "job_title": sc.job_title}


class AgentSkillDispatcher:
    """按 intent 分发工具 handler（doc 44：真实执行；邮件/试卷留接口）。"""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {
            "jd": self._handle_jd,
            "jd_edit": self._handle_jd_edit,
            "criteria_edit": self._handle_criteria_edit,
            "resume_screening": self._handle_resume_screening,
            "interview_plan": self._handle_interview_plan,
            "resource_delete": self._handle_resource_delete,
        }

    def is_registered(self, intent: str) -> bool:
        return intent in self._handlers

    async def dispatch(
        self, intent: str, params: dict[str, Any], user: User, db: AsyncSession
    ) -> ToolOutcome:
        """分发到注册的 handler；清单外 intent 抛 ValueError（边界先天）。"""
        if intent not in self._handlers:
            raise ValueError(f"未注册的工具 intent: {intent}")
        return await self._handlers[intent](params, user, db)

    # ---------- 6 工具 handler ----------

    async def _handle_jd(self, params: dict[str, Any], user: User, db: AsyncSession) -> ToolOutcome:
        """生成 JD（type=1）：缺岗位名称追问；否则生成初稿 → jd_confirm 面板。"""
        message = params.get("message", "")
        title = _extract_target(message)
        if not title:
            return ToolOutcome(
                missing_fields=["job_title"],
                artifacts=[{"type": "requirements", "intent": "jd", "missing_fields": ["job_title"]}],
            )
        draft = await job_description_service.generate_jd(
            JDGenerateRequest(title=title, description=message)
        )
        return ToolOutcome(
            artifacts=[
                {
                    "type": "jd_confirm",
                    "intent": "jd",
                    "route": TOOL_SPECS["jd"]["route"],
                    "draft": draft.model_dump(mode="json"),
                }
            ],
            suggestions=["保存并发布 JD", "生成评分标准"],
        )

    async def _handle_jd_edit(self, params: dict[str, Any], user: User, db: AsyncSession) -> ToolOutcome:
        """编辑 JD：按标题定位（0/1/N 命中 → 无匹配 / 编辑请求 / 候选列表）。"""
        message = params.get("message", "")
        target = _extract_target(message)
        jds = await job_description_service.list_jds(db)
        if not target:
            return ToolOutcome(
                missing_fields=["target"],
                artifacts=[{"type": "jd_edit_request", "intent": "jd_edit", "found": False}],
                message="请指明要修改哪份 JD（如「修改前端工程师的 JD」）。",
            )
        matches = [j for j in jds if target in (j.title or "")]
        if not matches:
            return ToolOutcome(
                artifacts=[{"type": "jd_edit_request", "intent": "jd_edit", "target": target, "found": False}],
                message=f"未找到标题包含「{target}」的 JD，请先到 JD 生成页创建。",
            )
        if len(matches) > 1:
            return ToolOutcome(
                artifacts=[
                    {
                        "type": "jd_edit_candidates",
                        "intent": "jd_edit",
                        "candidates": [_jd_brief(j) for j in matches],
                    }
                ],
                message="找到多份 JD，请指明要修改哪一份。",
            )
        j = matches[0]
        return ToolOutcome(
            artifacts=[
                {
                    "type": "jd_edit_request",
                    "intent": "jd_edit",
                    "route": TOOL_SPECS["jd_edit"]["route"],
                    "jd_id": str(j.id),
                    "title": j.title,
                }
            ],
            message=f"已定位 JD「{j.title}」，请描述要修改的内容（编辑将跳转 JD 页完成）。",
        )

    async def _handle_criteria_edit(
        self, params: dict[str, Any], user: User, db: AsyncSession
    ) -> ToolOutcome:
        """编辑评分标准：按标题定位（0/1/N 命中 → 无匹配 / 编辑请求 / 候选列表）。"""
        message = params.get("message", "")
        target = _extract_target(message)
        criteria = await scoring_criteria_service.list_scoring_criteria(db)
        if not target:
            return ToolOutcome(
                missing_fields=["target"],
                artifacts=[{"type": "criteria_edit_request", "intent": "criteria_edit", "found": False}],
                message="请指明要修改哪份评分标准（如「修改前端工程师的评分标准」）。",
            )
        matches = [c for c in criteria if target in (c.title or "") or target in (c.job_title or "")]
        if not matches:
            return ToolOutcome(
                artifacts=[
                    {"type": "criteria_edit_request", "intent": "criteria_edit", "target": target, "found": False}
                ],
                message=f"未找到与「{target}」相关的评分标准，请先到评分标准页生成。",
            )
        if len(matches) > 1:
            return ToolOutcome(
                artifacts=[
                    {
                        "type": "criteria_edit_candidates",
                        "intent": "criteria_edit",
                        "candidates": [_criteria_brief(c) for c in matches],
                    }
                ],
                message="找到多份评分标准，请指明要修改哪一份。",
            )
        c = matches[0]
        return ToolOutcome(
            artifacts=[
                {
                    "type": "criteria_edit_request",
                    "intent": "criteria_edit",
                    "route": TOOL_SPECS["criteria_edit"]["route"],
                    "criteria_id": str(c.id),
                    "title": c.title,
                }
            ],
            message=f"已定位评分标准「{c.title}」，请描述要修改的内容。",
        )

    async def _handle_resume_screening(
        self, params: dict[str, Any], user: User, db: AsyncSession
    ) -> ToolOutcome:
        """简历评估：对话入口仅做上传引导（实际评估在简历筛选页完成，文件内容不进入对话）。"""
        attachments = params.get("attachments") or []
        has_resume = any("resume" in a or "简历" in a for a in attachments)
        if not has_resume:
            return ToolOutcome(
                missing_fields=["resume_file"],
                artifacts=[
                    {
                        "type": "resume_upload_request",
                        "intent": "resume_screening",
                        "route": TOOL_SPECS["resume_screening"]["route"],
                    }
                ],
                message="请先上传简历文件（PDF/DOC/DOCX），并选择匹配的 JD。可跳转简历筛选页完成上传与评估。",
            )
        return ToolOutcome(
            artifacts=[
                {
                    "type": "resume_screening_results",
                    "intent": "resume_screening",
                    "route": TOOL_SPECS["resume_screening"]["route"],
                    "guide": True,
                }
            ],
            message="已收到简历附件，请到简历筛选页选择 JD 并完成评估。",
        )

    async def _handle_interview_plan(
        self, params: dict[str, Any], user: User, db: AsyncSession
    ) -> ToolOutcome:
        """面试方案：`resolve_candidate` 四态，仅 matched 生成方案。"""
        message = params.get("message", "")
        candidates = await resume_evaluation_service.list_evaluations(user, db)
        scored = [c for c in candidates if c.total_score is not None]
        query = _extract_candidate(message)
        resolution = interview_plan_service.resolve_candidate(query, scored)

        if resolution.state == "matched":
            ev = resolution.matches[0]
            try:
                plan = await interview_plan_service.generate_plan(
                    InterviewPlanGenerateRequest(resume_evaluation_id=ev.id), user, db
                )
            except HTTPException as exc:
                return ToolOutcome(
                    artifacts=[{"type": "interview_plan_request", "intent": "interview_plan", "state": "no_match"}],
                    message=str(exc.detail),
                )
            return ToolOutcome(
                artifacts=[
                    {
                        "type": "interview_plan_execute",
                        "intent": "interview_plan",
                        "route": TOOL_SPECS["interview_plan"]["route"],
                        "plan_id": str(plan.id),
                        "candidate_name": plan.candidate_name,
                        "content": plan.content,
                    }
                ],
                message=f"已为候选人「{plan.candidate_name}」生成面试方案。",
                suggestions=["查看面试方案", "导出方案"],
            )

        if resolution.state == "ambiguous":
            return ToolOutcome(
                artifacts=[
                    {
                        "type": "interview_plan_request",
                        "intent": "interview_plan",
                        "state": "ambiguous",
                        "candidates": [{"name": c.candidate_name} for c in resolution.matches],
                    }
                ],
                message="候选人指代有歧义，请说明得更具体（如「为张三生成面试方案」）。",
            )
        if resolution.state == "no_match":
            return ToolOutcome(
                artifacts=[{"type": "interview_plan_request", "intent": "interview_plan", "state": "no_match"}],
                message=resolution.message + "。请先到简历筛选页完成评估。",
            )
        return ToolOutcome(
            artifacts=[{"type": "interview_plan_request", "intent": "interview_plan", "state": "no_specific"}],
            message="请指明为哪位候选人生成面试方案（如「为张三生成面试方案」）。",
        )

    async def _handle_resource_delete(
        self, params: dict[str, Any], user: User, db: AsyncSession
    ) -> ToolOutcome:
        """删除资源：两步确认。首轮出候选 + requires_confirmation；「确认删除」后真实执行。"""
        message = params.get("message", "")
        is_confirm = any(k in message for k in ("确认", "确定"))
        parsed = agent_core._parse_delete_request(message) or agent_core._fallback_parse_delete_request(message)
        resource_type = (parsed or {}).get("resource_type")

        if not is_confirm:
            candidates = await self._list_delete_candidates(resource_type, message, db)
            return ToolOutcome(
                artifacts=[
                    {
                        "type": "delete_resource_candidates",
                        "intent": "resource_delete",
                        "resource_type": resource_type,
                        "candidates": candidates,
                    }
                ],
                requires_confirmation=True,
                message=f"找到 {len(candidates)} 条资源，请回复「确认删除 …」执行。"
                if candidates
                else "未找到可删除的资源，请指明具体名称。",
            )

        # 确认阶段：真实删除
        deleted, error = await self._execute_delete(resource_type, message, db)
        if deleted is None:
            return ToolOutcome(
                artifacts=[
                    {
                        "type": "delete_resource_candidates",
                        "intent": "resource_delete",
                        "resource_type": resource_type,
                        "candidates": [],
                    }
                ],
                requires_confirmation=True,
                message=error or "无法定位唯一删除目标，请指明具体名称。",
            )
        return ToolOutcome(
            artifacts=[{"type": "delete_resource_result", "intent": "resource_delete", "deleted": deleted}],
            message=f"已删除：{deleted}。",
            executed=True,
        )

    # ---------- 删除候选与执行（JD / 评分标准；简历/面试/文档本期暂不支持删除） ----------

    async def _list_delete_candidates(
        self, resource_type: str | None, message: str, db: AsyncSession
    ) -> list[dict[str, Any]]:
        target = _extract_target(message)
        if resource_type == "jd":
            jds = await job_description_service.list_jds(db)
            return [
                {"id": str(j.id), "title": j.title, "type": "jd"}
                for j in jds
                if not target or target in (j.title or "")
            ]
        if resource_type == "scoring_criteria":
            scs = await scoring_criteria_service.list_scoring_criteria(db)
            return [
                {"id": str(s.id), "title": s.title, "type": "scoring_criteria"}
                for s in scs
                if not target or target in (s.title or "") or target in (s.job_title or "")
            ]
        return []

    async def _execute_delete(
        self, resource_type: str | None, message: str, db: AsyncSession
    ) -> tuple[str | None, str | None]:
        """真实删除，返回 `(已删除标题, 错误原因)`；有依赖时拒绝并说明（受控自动化，不级联）。"""
        target = _extract_target(message)
        if resource_type == "jd":
            jds = await job_description_service.list_jds(db)
            matches = [j for j in jds if target and target in (j.title or "")]
            if len(matches) != 1:
                return None, "无法定位唯一删除目标，请指明具体名称。"
            jd = matches[0]
            deps = await self._jd_dependents(jd, db)
            if deps:
                return None, f"JD「{jd.title}」存在关联的 {deps}，请先删除后再试。"
            await job_description_service.delete_jd(jd.id, db)
            return jd.title, None
        if resource_type == "scoring_criteria":
            scs = await scoring_criteria_service.list_scoring_criteria(db)
            matches = [s for s in scs if target and target in (s.title or "")]
            if len(matches) != 1:
                return None, "无法定位唯一删除目标，请指明具体名称。"
            sc = matches[0]
            deps = await self._criteria_dependents(sc, db)
            if deps:
                return None, f"评分标准「{sc.title}」存在关联的 {deps}，请先删除后再试。"
            await scoring_criteria_service.delete_scoring_criteria(sc.id, db)
            return sc.title, None
        return None, "暂不支持删除该类型资源。"

    async def _jd_dependents(self, jd: Any, db: AsyncSession) -> str | None:
        """JD 依赖的评分标准 / 简历评估（删除前提示，不级联）。"""
        sc = (
            await db.execute(
                select(func.count()).select_from(ScoringCriteria).where(
                    ScoringCriteria.job_description_id == jd.id
                )
            )
        ).scalar() or 0
        re_ = (
            await db.execute(
                select(func.count()).select_from(ResumeEvaluation).where(
                    ResumeEvaluation.job_description_id == jd.id
                )
            )
        ).scalar() or 0
        parts = []
        if sc:
            parts.append(f"{sc} 份评分标准")
        if re_:
            parts.append(f"{re_} 份简历评估")
        return "、".join(parts) or None

    async def _criteria_dependents(self, sc: Any, db: AsyncSession) -> str | None:
        """评分标准依赖的简历评估（删除前提示，不级联）。"""
        re_ = (
            await db.execute(
                select(func.count()).select_from(ResumeEvaluation).where(
                    ResumeEvaluation.scoring_criteria_id == sc.id
                )
            )
        ).scalar() or 0
        return f"{re_} 份简历评估" if re_ else None


# 服务层共享的默认分发器
skill_dispatcher = AgentSkillDispatcher()
