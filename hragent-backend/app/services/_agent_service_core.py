"""AgentServiceCore（doc 16 §四/§五/§六 + doc 43）：计划与决策的确定性核心。

职责：工具注册表、角色 gating、缺口分类（缺信息/缺确认）、高风险锁定（删除解析）、
会话记忆组装、指代解析（最近产物）。所有方法确定性、无副作用、可单测；
工具的真实执行在 `agent_skills.AgentSkillDispatcher`（stub，见文档 44）。
"""
from __future__ import annotations

import re
from typing import Any, Sequence

from app.core.config import settings
from app.services.intent_service import JOB_TITLE_RE, TOOL_ROLES

# 18 种产物类型（doc 16 §7.2；exam/email 相关本期不做，仅保留边界）
ARTIFACT_TYPES: tuple[str, ...] = (
    "requirements",
    "jd_confirm",
    "job_description",
    "scoring_criteria",
    "resume_upload_request",
    "resume_screening_results",
    "resume_screening_followup",
    "interview_plan_execute",
    "interview_plan_request",
    "exam_document_upload_request",
    "exam_generate_request",
    "email_draft",
    "email_send_request",
    "delete_resource_result",
    "delete_resource_candidates",
    "jd_edit_request",
    "jd_edit_candidates",
    "criteria_edit_request",
    "criteria_edit_candidates",
    "error_recovery",
)

# 本期 6 工具注册表（doc 16 §二 / doc 43；handler 均为 stub）
TOOL_SPECS: dict[str, dict[str, Any]] = {
    "jd": {"name": "生成 JD", "route": "recruitment.jd", "roles": TOOL_ROLES},
    "jd_edit": {"name": "编辑 JD", "route": "recruitment.jd", "roles": TOOL_ROLES},
    "criteria_edit": {"name": "编辑评分标准", "route": "recruitment.scoring", "roles": TOOL_ROLES},
    "resume_screening": {"name": "简历评估", "route": "recruitment.resume", "roles": TOOL_ROLES},
    "interview_plan": {"name": "生成面试方案", "route": "recruitment.interview", "roles": TOOL_ROLES},
    "resource_delete": {
        "name": "删除资源",
        "route": None,
        "roles": TOOL_ROLES,
        "requires_confirmation": True,
    },
}

# 删除目标关键词 → 资源类型（正则兜底解析，doc 16 §5.2）
DELETE_TARGET_LABELS: dict[str, str] = {
    "JD": "jd",
    "岗位": "jd",
    "评分标准": "scoring_criteria",
    "简历": "resume",
    "候选人": "resume",
    "面试方案": "interview_plan",
    "面试": "interview_plan",
    "文档": "document",
    "记录": "record",
}

# 会话记忆预算（doc 16 §六）
MEMORY_MAX_MESSAGES = 12
MEMORY_MAX_CHARS = 6000


class AgentServiceCore:
    """确定性决策核心：不调用 LLM，产出计划/缺口/锁定/记忆/指代。"""

    def _build_tool_registry(self) -> dict[str, dict[str, Any]]:
        """返回本期 6 工具注册表（含角色与高风险标记）。"""
        return dict(TOOL_SPECS)

    def _missing_required_fields(self, intent: str, message: str = "") -> list[str]:
        """缺口分类——缺「信息」（doc 16 §4.1）：JD 缺岗位名称则追问。

        仅对话层最小信号；地点/薪资/经验/学历由前端 JD 表单（文档 44）收集，避免连环追问。
        """
        if intent == "jd":
            return [] if JOB_TITLE_RE.search(message or "") else ["job_title"]
        return []

    def _parse_delete_request(self, message: str, memory: str | None = None) -> dict | None:
        """删除目标解析（LLM，doc 16 §5.2）；未配置/失败返回 None，由正则兜底。"""
        if not settings.llm_configured:
            return None
        try:
            return self._llm_parse_delete_remote(message, memory)
        except Exception:
            return None

    def _fallback_parse_delete_request(self, message: str) -> dict | None:
        """删除目标解析正则兜底：命中关键词返回资源类型，否则 None。"""
        m = message or ""
        for keyword, resource_type in DELETE_TARGET_LABELS.items():
            if keyword in m:
                return {"resource_type": resource_type, "raw": m}
        return None

    def _build_conversation_memory(
        self,
        messages: Sequence[Any],
        max_messages: int = MEMORY_MAX_MESSAGES,
        max_chars: int = MEMORY_MAX_CHARS,
    ) -> str:
        """会话记忆组装（doc 16 §六）：最近 N 条、累计字符上限，从新到旧截断。

        累计含消息间换行分隔符，保证返回文本严格 ≤ max_chars。
        """
        recent = list(messages)[-max_messages:]
        kept: list[str] = []
        total = 0
        for msg in reversed(recent):
            content = (msg.content or "").strip()
            if not content:
                continue
            sep = 1 if kept else 0  # 分隔符（换行）
            if total + sep + len(content) > max_chars:
                available = max_chars - total - sep
                if available > 0:
                    kept.append(content[:available])
                break
            kept.append(content)
            total += sep + len(content)
        return "\n".join(reversed(kept))

    def _recent_generated_resources(
        self, messages: Sequence[Any], resource_type: str | None = None
    ) -> list[dict]:
        """指代解析（doc 16 §六）：从历史 assistant 消息 artifacts 找「刚才那个产物」。"""
        found: list[dict] = []
        for msg in reversed(list(messages)):
            ctx = msg.context or {}
            if not isinstance(ctx, dict):
                continue
            artifacts = ctx.get("agent_response", {}).get("artifacts", [])
            for art in artifacts or []:
                if isinstance(art, dict) and (
                    resource_type is None or art.get("type") == resource_type
                ):
                    found.append(art)
        return found

    def check_role(self, intent: str, role: str) -> bool:
        """角色 gating（doc 14）：chat 人人可发；招聘/删除工具仅 admin/hr 可触发。"""
        if intent == "chat":
            return True
        spec = TOOL_SPECS.get(intent)
        return bool(spec) and role in spec["roles"]

    def _llm_parse_delete_remote(self, message: str, memory: str | None) -> dict:
        """LLM 删除目标解析（真实 API 未接入）。"""
        raise NotImplementedError("真实 LLM 删除解析尚未接入")


# 服务层共享的默认核心
agent_core = AgentServiceCore()
