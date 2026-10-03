"""对话消息实体（含回复树 parent_message_id）。"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(BaseModel):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(32), default=MessageRole.user.value, nullable=False
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # agent_response / 结构化上下文（工具调用、来源依据等）
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    feedback_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True
    )

    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="messages"
    )
    parent: Mapped[Message | None] = relationship(
        "Message", remote_side="Message.id", back_populates="replies"
    )
    replies: Mapped[list[Message]] = relationship("Message", back_populates="parent")
