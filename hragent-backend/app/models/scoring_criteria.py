"""评分标准实体（绑定 JD，可选）。"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.scoring_status import ScoringStatus


class ScoringCriteria(BaseModel):
    __tablename__ = "scoring_criteria"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    scoring_dimensions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=ScoringStatus.draft.value, nullable=False
    )
    job_description_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_descriptions.id"), nullable=True
    )
