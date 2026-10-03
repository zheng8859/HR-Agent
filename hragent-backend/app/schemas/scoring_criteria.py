"""评分标准请求/响应 schema。"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.scoring_status import ScoringStatus


class ScoringDimension(BaseModel):
    """评分维度：name / weight / max_score / description（doc 15 §2.2）。"""

    name: str
    weight: float
    max_score: float
    description: str = ""


class ScoringGenerateRequest(BaseModel):
    """基于 JD 生成评分标准。"""

    job_title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ScoringGenerated(BaseModel):
    """生成结果（未保存），附配平标志供人工确认。"""

    title: str
    job_title: str | None = None
    content: str
    total_score: int = 100
    dimensions: list[ScoringDimension]
    is_balanced: bool
    score_sum: float
    difference: float


class ScoringCriteriaCreate(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    job_title: str | None = None
    total_score: int = 100
    scoring_dimensions: list[ScoringDimension] | None = None
    criteria_data: dict | None = None
    status: str = ScoringStatus.draft.value
    job_description_id: uuid.UUID | None = None


class ScoringCriteriaUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    job_title: str | None = None
    total_score: int | None = None
    scoring_dimensions: list[ScoringDimension] | None = None
    criteria_data: dict | None = None
    status: str | None = None
    job_description_id: uuid.UUID | None = None


class ScoringCriteriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    job_title: str | None = None
    content: str | None = None
    criteria_data: dict | None = None
    total_score: int
    scoring_dimensions: list | None = None
    status: str
    job_description_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
