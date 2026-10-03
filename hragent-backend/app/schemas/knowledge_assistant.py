"""知识问答请求/响应 schema（doc 40）。"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class KnowledgeAskRequest(BaseModel):
    """知识问答请求：问题 + 可选知识库。"""

    question: str = Field(min_length=1, max_length=2000)
    knowledge_base_id: uuid.UUID | None = None


class DocumentChunkRef(BaseModel):
    """来源片段：命中文档 + 最相关切片 + 相似度。"""

    document_id: uuid.UUID
    document_name: str
    chunk_text: str
    similarity: float


class KnowledgeAskResponse(BaseModel):
    """知识问答响应：回答 + 是否答出 + 置信度 + 意图 + 改写 + 来源。"""

    answer: str
    answered: bool
    confidence: float
    intent: str  # "KB" | "GENERAL"
    rewritten_query: str | None = None
    expanded_keywords: list[str] = []
    document_chunks: list[DocumentChunkRef] = []
