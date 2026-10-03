"""会话端点（doc 17 §2.2 / doc 43）：会话 CRUD，仅返回本人数据（所有权隔离）。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.conversation import ConversationCreate, ConversationDetail, ConversationRead
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationRead, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationRead:
    return await conversation_service.create_conversation(user, db, payload.title)


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationRead]:
    return await conversation_service.list_conversations(user, db)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    conv = await conversation_service.get_conversation(user, conversation_id, db)
    messages = await conversation_service.list_messages(user, conversation_id, db)
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        status=conv.status,
        user_id=conv.user_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages,
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await conversation_service.delete_conversation(user, conversation_id, db)
