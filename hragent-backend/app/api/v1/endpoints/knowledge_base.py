"""知识库端点：CRUD。

写操作（POST/PUT/DELETE）走 `get_current_admin_by_role`；
读操作（GET）走 `get_current_user`（知识库为共享资源，不按 user_id 隔离）。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin_by_role, get_current_user
from app.models import User
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.services import knowledge_base_service as svc

router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


@router.post("", response_model=KnowledgeBaseRead, status_code=201)
async def create_kb(
    request: KnowledgeBaseCreate,
    _user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseRead:
    return await svc.create_kb(request, db)


@router.get("", response_model=list[KnowledgeBaseRead])
async def list_kbs(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeBaseRead]:
    return await svc.list_kbs(db)


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
async def get_kb(
    kb_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseRead:
    return await svc.get_kb(kb_id, db)


@router.put("/{kb_id}", response_model=KnowledgeBaseRead)
async def update_kb(
    kb_id: uuid.UUID,
    request: KnowledgeBaseUpdate,
    _user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseRead:
    return await svc.update_kb(kb_id, request, db)


@router.delete("/{kb_id}", status_code=204)
async def delete_kb(
    kb_id: uuid.UUID,
    _user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> None:
    await svc.delete_kb(kb_id, db)
