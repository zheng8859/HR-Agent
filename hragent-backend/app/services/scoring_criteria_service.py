"""评分标准生成服务：维度结构、权重配平校验（不配平只提示、不自动修正）、绑定 JD。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobDescription, ScoringCriteria, ScoringStatus
from app.schemas.scoring_criteria import (
    ScoringCriteriaCreate,
    ScoringCriteriaUpdate,
    ScoringDimension,
    ScoringGenerateRequest,
    ScoringGenerated,
)
from app.services.dify_service import dify_client


@dataclass(frozen=True)
class BalanceResult:
    is_balanced: bool
    score_sum: float
    difference: float


def validate_balance(
    dimensions: list[ScoringDimension], total_score: int
) -> BalanceResult:
    """校验维度分值之和是否等于总分。不配平仅返回标志与差值，绝不自动改写。"""
    score_sum = sum(d.max_score for d in dimensions)
    difference = total_score - score_sum
    return BalanceResult(
        is_balanced=abs(difference) < 1e-9,
        score_sum=score_sum,
        difference=difference,
    )


async def generate_scoring_criteria(
    request: ScoringGenerateRequest,
) -> ScoringGenerated:
    output = await dify_client.run_scoring_workflow(
        {"job_title": request.job_title, "job_content": request.content or ""}
    )
    dimensions = [ScoringDimension(**d) for d in output.get("dimensions", [])]
    total_score = int(output.get("total_score", 100))
    balance = validate_balance(dimensions, total_score)
    return ScoringGenerated(
        title=output.get("title") or f"{request.job_title} 评分标准",
        job_title=request.job_title,
        content=output.get("content", ""),
        total_score=total_score,
        dimensions=dimensions,
        is_balanced=balance.is_balanced,
        score_sum=balance.score_sum,
        difference=balance.difference,
    )


def _dimensions_to_dicts(dimensions: list[ScoringDimension] | None) -> list[dict] | None:
    if dimensions is None:
        return None
    return [d.model_dump() for d in dimensions]


# ---------- CRUD 与绑定 ----------


async def list_scoring_criteria(db: AsyncSession) -> list[ScoringCriteria]:
    result = await db.execute(
        select(ScoringCriteria).order_by(ScoringCriteria.created_at.desc())
    )
    return list(result.scalars().all())


async def get_scoring_criteria(
    criteria_id: uuid.UUID, db: AsyncSession
) -> ScoringCriteria:
    sc = await db.get(ScoringCriteria, criteria_id)
    if sc is None:
        raise HTTPException(status_code=404, detail="评分标准不存在")
    return sc


async def create_scoring_criteria(
    schema: ScoringCriteriaCreate, db: AsyncSession
) -> ScoringCriteria:
    if schema.job_description_id is not None:
        jd = await db.get(JobDescription, schema.job_description_id)
        if jd is None:
            raise HTTPException(status_code=404, detail="绑定的 JD 不存在")
    sc = ScoringCriteria(
        title=schema.title,
        content=schema.content,
        job_title=schema.job_title,
        total_score=schema.total_score,
        scoring_dimensions=_dimensions_to_dicts(schema.scoring_dimensions),
        criteria_data=schema.criteria_data,
        status=schema.status,
        job_description_id=schema.job_description_id,
    )
    db.add(sc)
    await db.flush()
    return sc


async def update_scoring_criteria(
    criteria_id: uuid.UUID, schema: ScoringCriteriaUpdate, db: AsyncSession
) -> ScoringCriteria:
    sc = await get_scoring_criteria(criteria_id, db)
    if schema.job_description_id is not None:
        jd = await db.get(JobDescription, schema.job_description_id)
        if jd is None:
            raise HTTPException(status_code=404, detail="绑定的 JD 不存在")
    data = schema.model_dump(exclude_unset=True)
    if "scoring_dimensions" in data:
        data["scoring_dimensions"] = _dimensions_to_dicts(schema.scoring_dimensions)
    for key, value in data.items():
        setattr(sc, key, value)
    await db.flush()
    return sc


async def change_status(
    criteria_id: uuid.UUID, status: str, db: AsyncSession
) -> ScoringCriteria:
    if status not in ScoringStatus._value2member_map_:
        raise HTTPException(status_code=422, detail="非法评分标准状态")
    sc = await get_scoring_criteria(criteria_id, db)
    sc.status = status
    await db.flush()
    return sc


async def delete_scoring_criteria(
    criteria_id: uuid.UUID, db: AsyncSession
) -> None:
    sc = await get_scoring_criteria(criteria_id, db)
    await db.delete(sc)
    await db.flush()
