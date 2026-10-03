"""简历评估实体（绑定 JD + 评分标准）。"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ResumeEvaluationStatus(str, enum.Enum):
    pending = "pending"
    rejected = "rejected"
    interview = "interview"


class ResumeEvaluation(BaseModel):
    __tablename__ = "resume_evaluations"

    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resume_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    work_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(128), nullable=True)
    school: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluation_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=ResumeEvaluationStatus.pending.value, nullable=False
    )
    job_description_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_descriptions.id"), nullable=True
    )
    scoring_criteria_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scoring_criteria.id"), nullable=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
