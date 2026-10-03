"""知识库实体。"""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class KnowledgeBase(BaseModel):
    __tablename__ = "knowledge_bases"

    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_searchable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)

    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="knowledge_base"
    )
