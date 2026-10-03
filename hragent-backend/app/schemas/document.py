"""文档请求/响应 schema（doc 39）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    original_filename: str | None = None
    file_path: str | None = None
    file_size: int | None = None
    file_hash: str | None = None
    mime_type: str | None = None
    category: str | None = None
    tags: str | None = None
    status: str
    chunk_count: int
    error_message: str | None = None
    knowledge_base_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class DocumentChunksRead(BaseModel):
    """文档语义切片（前端「查看切片」）。"""

    chunks: list[str]
