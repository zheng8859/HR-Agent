"""Agent 编排请求/响应 schema（doc 16 §7.1 / doc 43）。

`AgentChatResponse` 必含 8 个契约字段（与 doc 42 `AGENT_CONTRACT_FIELDS` 一致）：
message / intent / route / steps / artifacts / suggestions / requires_confirmation / missing_fields。
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """对话请求：消息 + 可选会话 + 附件类型提示（如 "resume"）。"""

    message: str = Field(min_length=1)
    conversation_id: uuid.UUID | None = None
    attachments: list[str] = Field(default_factory=list)


class IntentClassifyRequest(BaseModel):
    message: str = Field(min_length=1)
    attachments: list[str] = Field(default_factory=list)


class IntentClassifyResponse(BaseModel):
    """意图识别结果：动作空间 chat / use_tool / ask_user。"""

    intent: str
    route: str
    tool: str | None = None
    action: str = "chat"
    requires_confirmation: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    source: str = "fast"  # fast / slow / fallback


class AgentStep(BaseModel):
    """执行步骤（进度折叠面板展示）。"""

    id: str
    title: str
    status: str = "pending"  # pending / running / completed / failed
    detail: str | None = None
    tool: str | None = None


class AgentChatResponse(BaseModel):
    """Agent 完整响应（8 契约字段 + conversation_id + source）。"""

    message: str
    intent: str
    route: str
    steps: list[AgentStep] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    conversation_id: uuid.UUID | None = None
    source: str = "fast"
