"""知识库请求/响应 schema（doc 39）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    """新建知识库（写操作）。"""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_public: bool = False
    is_searchable: bool = True
    meta_data: dict | None = None
    category: str | None = None
    tags: str | None = None


class KnowledgeBaseUpdate(BaseModel):
    """编辑知识库（全部可选）。"""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_public: bool | None = None
    is_searchable: bool | None = None
    meta_data: dict | None = None
    category: str | None = None
    tags: str | None = None


class KnowledgeBaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    is_public: bool
    is_searchable: bool
    meta_data: dict | None = None
    document_count: int
    category: str | None = None
    tags: str | None = None
    created_at: datetime
    updated_at: datetime
