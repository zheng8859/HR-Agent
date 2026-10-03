"""面试方案请求/响应 schema（doc 15 §2.4 + doc 38）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InterviewPlanGenerateRequest(BaseModel):
    """生成面试方案：绑定一条已完成简历评估（防空转）。"""

    resume_evaluation_id: uuid.UUID


class InterviewPlanUpdate(BaseModel):
    """编辑保存（受控自动化：AI 出初稿、人定终稿）。"""

    content: str | None = Field(default=None, min_length=1)
    candidate_name: str | None = Field(default=None, min_length=1)


class InterviewPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_name: str | None = None
    candidate_position: str | None = None
    content: str | None = None
    resume_evaluation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
