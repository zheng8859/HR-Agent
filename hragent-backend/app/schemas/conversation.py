"""会话 / 消息 schema（doc 17 §2.2 + doc 43）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None = None
    status: str
    user_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str | None = None
    context: dict | None = None
    feedback_score: int | None = None
    parent_message_id: uuid.UUID | None = None
    created_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead] = Field(default_factory=list)


class FeedbackCreate(BaseModel):
    message_id: uuid.UUID
    score: int = Field(ge=1, le=5)


class FeedbackRead(BaseModel):
    message_id: uuid.UUID
    feedback_score: int
