"""JD 端点：生成（阻塞/流式）、需求解析、CRUD 与状态机。

写操作（生成/保存/编辑/删除/状态变更）走 `get_current_admin_by_role` 后端鉴权
（doc 14 权限矩阵：admin / hr_manager / hr_specialist）。
"""
from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin_by_role, get_current_user
from app.models import User
from app.schemas.job_description import (
    JDGenerateRequest,
    JDParsed,
    JDParseRequest,
    JobDescriptionCreate,
    JobDescriptionRead,
    JobDescriptionUpdate,
)
from app.services import job_description_service as jd_svc

router = APIRouter(prefix="/job-descriptions", tags=["job-descriptions"])


def _to_sse(events: AsyncIterator[dict]) -> AsyncIterator[str]:
    async def gen() -> AsyncIterator[str]:
        async for ev in events:
            yield f"event: {ev['event']}\n"
            yield f"data: {json.dumps(ev['data'], ensure_ascii=False)}\n\n"

    return gen()


@router.post("/generate", response_model=JobDescriptionCreate)
async def generate(
    request: JDGenerateRequest,
    _: User = Depends(get_current_admin_by_role),
) -> JobDescriptionCreate:
    return await jd_svc.generate_jd(request)


@router.post("/generate-stream")
async def generate_stream(
    request: JDGenerateRequest,
    _: User = Depends(get_current_admin_by_role),
) -> StreamingResponse:
    return StreamingResponse(
        _to_sse(jd_svc.generate_jd_stream(request)),
        media_type="text/event-stream",
    )


@router.post("/parse", response_model=JDParsed)
async def parse(
    request: JDParseRequest,
    _: User = Depends(get_current_admin_by_role),
) -> JDParsed:
    return await jd_svc.parse_requirement(request.text)


@router.get("", response_model=list[JobDescriptionRead])
async def list_jds(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JobDescriptionRead]:
    return await jd_svc.list_jds(db)


@router.get("/{jd_id}", response_model=JobDescriptionRead)
async def get_jd(
    jd_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobDescriptionRead:
    return await jd_svc.get_jd(jd_id, db)


@router.post("", response_model=JobDescriptionRead, status_code=201)
async def create_jd(
    schema: JobDescriptionCreate,
    current_user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> JobDescriptionRead:
    return await jd_svc.create_jd(schema, current_user, db)


@router.put("/{jd_id}", response_model=JobDescriptionRead)
async def update_jd(
    jd_id: uuid.UUID,
    schema: JobDescriptionUpdate,
    _: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> JobDescriptionRead:
    return await jd_svc.update_jd(jd_id, schema, db)


@router.patch("/{jd_id}/status", response_model=JobDescriptionRead)
async def change_status(
    jd_id: uuid.UUID,
    status: str = Query(...),
    _: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> JobDescriptionRead:
    return await jd_svc.change_status(jd_id, status, db)


@router.delete("/{jd_id}", status_code=204)
async def delete_jd(
    jd_id: uuid.UUID,
    _: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> None:
    await jd_svc.delete_jd(jd_id, db)
