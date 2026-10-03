"""JD 请求/响应 schema。"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.jd_status import JDStatus


class JDGenerateRequest(BaseModel):
    """生成请求：表单字段直生，或仅一句话描述（description）先解析。"""

    title: str | None = None
    department: str | None = None
    location: str | None = None
    salary_range: str | None = None
    experience_level: str | None = None
    education: str | None = None
    job_type: str | None = None
    skills: list[str] | None = None
    requirements: list[str] | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _require_title_or_description(self) -> "JDGenerateRequest":
        if not self.title and not self.description:
            raise ValueError("岗位名称或岗位需求描述至少填一项")
        return self


class JDParseRequest(BaseModel):
    text: str = Field(min_length=1)


class JDParsed(BaseModel):
    """一句话解析出的结构化字段。"""

    title: str | None = None
    department: str | None = None
    location: str | None = None
    salary_range: str | None = None
    experience_level: str | None = None
    education: str | None = None
    job_type: str | None = None
    skills: list[str] | None = None
    requirements: list[str] | None = None


class JobDescriptionCreate(BaseModel):
    """保存 JD：标题与正文必填（doc 13「保存时标题和正文必填」）。"""

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    department: str | None = None
    location: str | None = None
    salary_range: str | None = None
    experience_level: str | None = None
    education: str | None = None
    job_type: str | None = None
    skills: list[str] | None = None
    requirements: list[str] | None = None
    status: str = JDStatus.draft.value


class JobDescriptionUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    department: str | None = None
    location: str | None = None
    salary_range: str | None = None
    experience_level: str | None = None
    education: str | None = None
    job_type: str | None = None
    skills: list[str] | None = None
    requirements: list[str] | None = None
    status: str | None = None


class JobDescriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    department: str | None = None
    location: str | None = None
    salary_range: str | None = None
    experience_level: str | None = None
    education: str | None = None
    job_type: str | None = None
    skills: list | None = None
    content: str | None = None
    requirements: list | None = None
    status: str
    created_at: datetime
    updated_at: datetime
