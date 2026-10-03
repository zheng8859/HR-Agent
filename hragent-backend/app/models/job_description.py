"""招聘 JD 实体（四环节闭环起点）。"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.jd_status import JDStatus


class JobDescription(BaseModel):
    __tablename__ = "job_descriptions"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(128), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(128), nullable=True)
    education: Mapped[str | None] = mapped_column(String(128), nullable=True)
    job_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=JDStatus.draft.value, nullable=False
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True
    )
    workflow_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
