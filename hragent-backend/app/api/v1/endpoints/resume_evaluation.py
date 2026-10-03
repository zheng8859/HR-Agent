"""简历评估端点：上传、评估、状态流转、导出。

写操作（upload/evaluate/evaluate-auto/status）走 `get_current_admin_by_role`；
读操作（list/get/export）走 `get_current_user` 并按 `user_id` 过滤（简历属敏感信息）。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin_by_role, get_current_user
from app.models import User
from app.schemas.resume_evaluation import (
    ResumeAutoEvaluateRequest,
    ResumeEvaluateRequest,
    ResumeEvaluationRead,
    ResumeExport,
    ResumeUploadResult,
)
from app.services import resume_evaluation_service as svc

router = APIRouter(prefix="/resume-evaluation", tags=["resume-evaluation"])


@router.post("/upload", response_model=ResumeUploadResult)
async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_admin_by_role),
) -> ResumeUploadResult:
    return await svc.upload_resume(file, user)


@router.post("/evaluate", response_model=ResumeEvaluationRead, status_code=201)
async def evaluate(
    request: ResumeEvaluateRequest,
    user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> ResumeEvaluationRead:
    return await svc.evaluate(request, user, db)


@router.post("/evaluate-auto", response_model=ResumeEvaluationRead, status_code=201)
async def evaluate_auto(
    request: ResumeAutoEvaluateRequest,
    user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> ResumeEvaluationRead:
    return await svc.evaluate_auto(request, user, db)


@router.get("", response_model=list[ResumeEvaluationRead])
async def list_evaluations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ResumeEvaluationRead]:
    return await svc.list_evaluations(user, db)


@router.get("/{evaluation_id}", response_model=ResumeEvaluationRead)
async def get_evaluation(
    evaluation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeEvaluationRead:
    return await svc.get_evaluation(evaluation_id, user, db)


@router.patch("/{evaluation_id}/status", response_model=ResumeEvaluationRead)
async def update_status(
    evaluation_id: uuid.UUID,
    status: str = Query(...),
    user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> ResumeEvaluationRead:
    return await svc.update_status(evaluation_id, status, user, db)


@router.get("/{evaluation_id}/export", response_model=ResumeExport)
async def export_evaluation(
    evaluation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeExport:
    return await svc.export_evaluation(evaluation_id, user, db)
