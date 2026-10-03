"""评分标准端点：生成、CRUD、绑定 JD。写操作走 `get_current_admin_by_role`。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin_by_role, get_current_user
from app.models import User
from app.schemas.scoring_criteria import (
    ScoringCriteriaCreate,
    ScoringCriteriaRead,
    ScoringCriteriaUpdate,
    ScoringGenerated,
    ScoringGenerateRequest,
)
from app.services import scoring_criteria_service as sc_svc

router = APIRouter(prefix="/scoring-criteria", tags=["scoring-criteria"])


@router.post("/generate", response_model=ScoringGenerated)
async def generate(
    request: ScoringGenerateRequest,
    _: User = Depends(get_current_admin_by_role),
) -> ScoringGenerated:
    return await sc_svc.generate_scoring_criteria(request)


@router.get("", response_model=list[ScoringCriteriaRead])
async def list_scoring_criteria(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScoringCriteriaRead]:
    return await sc_svc.list_scoring_criteria(db)


@router.get("/{criteria_id}", response_model=ScoringCriteriaRead)
async def get_scoring_criteria(
    criteria_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoringCriteriaRead:
    return await sc_svc.get_scoring_criteria(criteria_id, db)


@router.post("", response_model=ScoringCriteriaRead, status_code=201)
async def create_scoring_criteria(
    schema: ScoringCriteriaCreate,
    _: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> ScoringCriteriaRead:
    return await sc_svc.create_scoring_criteria(schema, db)


@router.put("/{criteria_id}", response_model=ScoringCriteriaRead)
async def update_scoring_criteria(
    criteria_id: uuid.UUID,
    schema: ScoringCriteriaUpdate,
    _: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> ScoringCriteriaRead:
    return await sc_svc.update_scoring_criteria(criteria_id, schema, db)


@router.patch("/{criteria_id}/status", response_model=ScoringCriteriaRead)
async def change_status(
    criteria_id: uuid.UUID,
    status: str = Query(...),
    _: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> ScoringCriteriaRead:
    return await sc_svc.change_status(criteria_id, status, db)


@router.delete("/{criteria_id}", status_code=204)
async def delete_scoring_criteria(
    criteria_id: uuid.UUID,
    _: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> None:
    await sc_svc.delete_scoring_criteria(criteria_id, db)
