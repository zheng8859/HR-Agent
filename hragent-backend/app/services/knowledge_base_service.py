"""知识库服务：CRUD、名称唯一、含文档拒绝删除（doc 39 §知识库 CRUD）。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


async def _ensure_name_unique(name: str, db: AsyncSession, exclude_id: uuid.UUID | None = None) -> None:
    stmt = select(KnowledgeBase).where(KnowledgeBase.name == name)
    if exclude_id is not None:
        stmt = stmt.where(KnowledgeBase.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="知识库名称已存在")


async def create_kb(request: KnowledgeBaseCreate, db: AsyncSession) -> KnowledgeBase:
    await _ensure_name_unique(request.name, db)
    kb = KnowledgeBase(
        name=request.name,
        description=request.description,
        is_public=request.is_public,
        is_searchable=request.is_searchable,
        meta_data=request.meta_data,
        category=request.category,
        tags=request.tags,
    )
    db.add(kb)
    await db.flush()
    await db.refresh(kb)
    return kb


async def list_kbs(db: AsyncSession) -> list[KnowledgeBase]:
    result = await db.execute(
        select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
    )
    return list(result.scalars().all())


async def get_kb(kb_id: uuid.UUID, db: AsyncSession) -> KnowledgeBase:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return kb


async def update_kb(
    kb_id: uuid.UUID, request: KnowledgeBaseUpdate, db: AsyncSession
) -> KnowledgeBase:
    kb = await get_kb(kb_id, db)
    if request.name is not None and request.name != kb.name:
        await _ensure_name_unique(request.name, db, exclude_id=kb.id)
        kb.name = request.name
    if request.description is not None:
        kb.description = request.description
    if request.is_public is not None:
        kb.is_public = request.is_public
    if request.is_searchable is not None:
        kb.is_searchable = request.is_searchable
    if request.meta_data is not None:
        kb.meta_data = request.meta_data
    if request.category is not None:
        kb.category = request.category
    if request.tags is not None:
        kb.tags = request.tags
    await db.flush()
    await db.refresh(kb)
    return kb


async def delete_kb(kb_id: uuid.UUID, db: AsyncSession) -> None:
    kb = await get_kb(kb_id, db)
    count = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.knowledge_base_id == kb.id)
        )
    ).scalar_one()
    if count > 0:
        raise HTTPException(status_code=409, detail="知识库仍含文档，请先删除其中的文档")
    await db.delete(kb)
    await db.flush()
