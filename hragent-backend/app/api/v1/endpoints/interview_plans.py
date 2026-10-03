"""面试方案端点：生成、重新生成、编辑保存、导出。

写操作（generate/regenerate/PUT）走 `get_current_admin_by_role`；
读操作（list/get/export）走 `get_current_user` 并按 `user_id` 过滤（方案属敏感信息）。
导出返回 UTF-8 带 BOM 的文件响应，Windows 记事本打开不乱码（doc 38 A4）。
"""
from __future__ import annotations

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin_by_role, get_current_user
from app.models import User
from app.schemas.interview_plan import (
    InterviewPlanGenerateRequest,
    InterviewPlanRead,
    InterviewPlanUpdate,
)
from app.services import interview_plan_service as svc

router = APIRouter(prefix="/interview-plans", tags=["interview-plans"])


@router.post("/generate", response_model=InterviewPlanRead, status_code=201)
async def generate(
    request: InterviewPlanGenerateRequest,
    user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> InterviewPlanRead:
    return await svc.generate_plan(request, user, db)


@router.post("/{plan_id}/regenerate", response_model=InterviewPlanRead)
async def regenerate(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> InterviewPlanRead:
    return await svc.regenerate_plan(plan_id, user, db)


@router.get("", response_model=list[InterviewPlanRead])
async def list_plans(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InterviewPlanRead]:
    return await svc.list_plans(user, db)


@router.get("/{plan_id}", response_model=InterviewPlanRead)
async def get_plan(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewPlanRead:
    return await svc.get_plan(plan_id, user, db)


@router.put("/{plan_id}", response_model=InterviewPlanRead)
async def update_plan(
    plan_id: uuid.UUID,
    request: InterviewPlanUpdate,
    user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> InterviewPlanRead:
    return await svc.update_plan(plan_id, request, user, db)


@router.get("/{plan_id}/export")
async def export_plan(
    plan_id: uuid.UUID,
    format: str = Query("md"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if format not in ("md", "txt"):
        raise HTTPException(status_code=422, detail="仅支持 md 或 txt 导出格式")
    plan = await svc.get_plan(plan_id, user, db)
    content = plan.content or ""
    media_type = "text/markdown; charset=utf-8" if format == "md" else "text/plain; charset=utf-8"
    filename = quote(f"面试方案-{plan.candidate_name or '候选人'}.{format}")
    return Response(
        content="﻿" + content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
