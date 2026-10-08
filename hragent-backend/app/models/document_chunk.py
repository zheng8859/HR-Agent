"""文档切片实体（doc 15 §4.1：语义切片后逐段向量化，chunk 级 embedding）。

检索粒度为切片级：每个语义切片（≤500 字，`chunk_text` 产出）各自生成一条 1536 维向量，
检索时对同一文档的切片向量取 max-pool 得到文档向量分。这样长文档（如人事管理流程.docx
6376 字）不再被 `_MAX_EMBED_CHARS` 截断，靠后小节（资产分类）也能被语义向量召回。
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import BaseModel


class DocumentChunk(BaseModel):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
