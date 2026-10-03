"""简历评估请求/响应 schema（doc 15 §2.3 + doc 37）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.resume_evaluation import ResumeEvaluationStatus


class ResumeDimension(BaseModel):
    """评分维度：name / score / max / reason（可解释才可信，见 CLAUDE.md 六.4）。"""

    name: str
    score: float
    max: float
    reason: str = ""


class ResumeUploadResult(BaseModel):
    """文件上传后抽取的纯文本（尚未评估，落「可编辑态」）。"""

    original_filename: str
    file_type: str
    resume_content: str


class ResumeEvaluateRequest(BaseModel):
    """绑定 JD 评估简历（写操作）。"""

    resume_content: str = Field(min_length=1)
    job_description_id: uuid.UUID
    scoring_criteria_id: uuid.UUID | None = None
    original_filename: str | None = None
    file_type: str | None = None


class ResumeAutoEvaluateRequest(BaseModel):
    """不指定 JD，自动匹配（候选：按岗位名匹配已有 JD，否则取最新 JD）。"""

    resume_content: str = Field(min_length=1)
    scoring_criteria_id: uuid.UUID | None = None
    original_filename: str | None = None
    file_type: str | None = None


class ResumeEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str | None = None
    file_type: str | None = None
    resume_content: str | None = None
    candidate_name: str | None = None
    candidate_position: str | None = None
    age: int | None = None
    gender: str | None = None
    work_years: float | None = None
    education_level: str | None = None
    school: str | None = None
    total_score: float | None = None
    evaluation_metrics: list | None = None
    status: str
    job_description_id: uuid.UUID | None = None
    scoring_criteria_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class ResumeExport(BaseModel):
    """导出结果：候选摘要 + 五维度（含理由）。"""

    candidate_name: str | None = None
    candidate_position: str | None = None
    total_score: float | None = None
    dimensions: list[ResumeDimension]
    status: str = ResumeEvaluationStatus.pending.value
    text: str
