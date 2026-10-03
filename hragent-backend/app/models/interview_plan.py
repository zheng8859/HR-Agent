"""面试方案实体（防空转：必须绑定一条已完成简历评估）。"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class InterviewPlan(BaseModel):
    __tablename__ = "interview_plans"

    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 防空转：面试方案必须绑定一条简历评估记录（非空外键）
    resume_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_evaluations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
