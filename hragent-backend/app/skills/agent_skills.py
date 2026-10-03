"""Agent 技能分发器（doc 16 §二 / doc 43）：按 intent 分发到工具 handler。

本期 6 个工具 handler 均为 **stub**（返回占位产物），真实实现见文档 44。
Skill 扩展机制（`backend/skills/` 下 SKILL.md + skill.json + 脚本）本期仅留接口——
邮件通知（`hr-agent-email`）本期不做，但保留 `email_notification` 分发位。
"""
from __future__ import annotations

from typing import Any, Callable

from app.services._agent_service_core import TOOL_SPECS

# intent → 产物类型（doc 16 §7.2；stub 阶段返回占位产物）
ARTIFACT_BY_INTENT: dict[str, str] = {
    "jd": "job_description",
    "jd_edit": "jd_edit_request",
    "criteria_edit": "criteria_edit_request",
    "resume_screening": "resume_screening_results",
    "interview_plan": "interview_plan_request",
    "resource_delete": "delete_resource_result",
}


def _stub_artifact(intent: str, params: dict[str, Any]) -> dict[str, Any]:
    """生成占位产物（handler stub，真实实现在文档 44）。"""
    return {
        "type": ARTIFACT_BY_INTENT[intent],
        "title": TOOL_SPECS[intent]["name"],
        "route": TOOL_SPECS[intent]["route"],
        "placeholder": True,
        "intent": intent,
        "params": params or {},
    }


class AgentSkillDispatcher:
    """按 intent 分发工具 handler（本期 stub；邮件 Skill 留接口）。"""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., dict[str, Any]]] = {
            intent: lambda params=None, intent=intent, **_kwargs: _stub_artifact(intent, params or {})
            for intent in ARTIFACT_BY_INTENT
        }

    def is_registered(self, intent: str) -> bool:
        return intent in self._handlers

    def dispatch(self, intent: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """分发到注册的 handler；清单外 intent 抛 ValueError（边界先天）。"""
        if intent not in self._handlers:
            raise ValueError(f"未注册的工具 intent: {intent}")
        return self._handlers[intent](params=params or {})


# 服务层共享的默认分发器
skill_dispatcher = AgentSkillDispatcher()
