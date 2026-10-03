"""对话/消息 CRUD 与反馈（doc 17 §2.2 + doc 43）。

所有权隔离：会话与消息 list/get 仅返回本人（`user_id` 过滤），他人 404。
会话记忆组装复用 `agent_core._build_conversation_memory`（最近 12 条 / 6000 字符）。
"""
from __future__ import annotations

import uuid
from typing import Any, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message, User
from app.services._agent_service_core import agent_core


async def _get_owned_conversation(
    user: User, conversation_id: uuid.UUID, db: AsyncSession
) -> Conversation:
    conv = await db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conv


async def create_conversation(
    user: User, db: AsyncSession, title: str | None = None
) -> Conversation:
    conv = Conversation(title=title, user_id=user.id)
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


async def list_conversations(user: User, db: AsyncSession) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.status != "deleted")
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(
    user: User, conversation_id: uuid.UUID, db: AsyncSession
) -> Conversation:
    return await _get_owned_conversation(user, conversation_id, db)


async def delete_conversation(
    user: User, conversation_id: uuid.UUID, db: AsyncSession
) -> None:
    conv = await _get_owned_conversation(user, conversation_id, db)
    conv.status = "deleted"
    await db.flush()


async def add_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str | None,
    context: dict[str, Any] | None = None,
    parent_message_id: uuid.UUID | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        context=context,
        parent_message_id=parent_message_id,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def list_messages(
    user: User, conversation_id: uuid.UUID, db: AsyncSession
) -> list[Message]:
    await _get_owned_conversation(user, conversation_id, db)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def add_feedback(
    user: User, message_id: uuid.UUID, score: int, db: AsyncSession
) -> Message:
    msg = await db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="消息不存在")
    # 所有权：消息必须属于本人的会话
    await _get_owned_conversation(user, msg.conversation_id, db)
    msg.feedback_score = score
    await db.flush()
    await db.refresh(msg)
    return msg


async def build_memory(
    user: User, conversation_id: uuid.UUID, db: AsyncSession
) -> str:
    """组装会话上下文记忆（最近 12 条 / 6000 字符）。"""
    messages = await list_messages(user, conversation_id, db)
    return agent_core._build_conversation_memory(messages)


def recent_generated_resources(messages: Sequence[Message], resource_type: str | None = None) -> list[dict]:
    """从历史 assistant 消息 artifacts 找最近产物（指代解析）。"""
    return agent_core._recent_generated_resources(messages, resource_type)
