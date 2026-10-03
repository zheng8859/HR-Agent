"""文档端点：上传、列表、详情、切片、重新处理、删除。

写操作（upload/reprocess/delete）走 `get_current_admin_by_role`；
读操作（list/get/chunks）走 `get_current_user` 并按 `user_id` 过滤（文档属敏感信息）。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin_by_role, get_current_user
from app.models import User
from app.schemas.document import DocumentChunksRead, DocumentRead
from app.services import enhanced_document_service as svc

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentRead, status_code=201)
async def upload(
    file: UploadFile = File(...),
    knowledge_base_id: uuid.UUID | None = Form(None),
    category: str | None = Form(None),
    tags: str | None = Form(None),
    user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    return await svc.upload_document(file, knowledge_base_id, category, tags, user, db)


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    knowledge_base_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentRead]:
    return await svc.list_documents(user, db, knowledge_base_id)


@router.get("/{doc_id}", response_model=DocumentRead)
async def get_document(
    doc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    return await svc.get_document(doc_id, user, db)


@router.get("/{doc_id}/chunks", response_model=DocumentChunksRead)
async def get_chunks(
    doc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentChunksRead:
    return DocumentChunksRead(chunks=await svc.get_document_chunks(doc_id, user, db))


@router.post("/{doc_id}/reprocess", response_model=DocumentRead)
async def reprocess(
    doc_id: uuid.UUID,
    user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    return await svc.reprocess_document(doc_id, user, db)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> None:
    await svc.delete_document(doc_id, user, db)
