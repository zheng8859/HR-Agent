"""JD 生成服务：双入口生成、需求解析、SSE 流式、CRUD 与状态机。

「AI 出初稿、人定终稿」：生成只返回初稿（不落库），保存才写入 `JobDescription`。
"""
from __future__ import annotations

import re
import uuid
from typing import AsyncIterator

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JDStatus, JobDescription, User
from app.schemas.job_description import (
    JDGenerateRequest,
    JDParsed,
    JobDescriptionCreate,
    JobDescriptionUpdate,
)
from app.services.dify_service import dify_client

_TITLE_PATTERNS = [
    r"招聘[（(]?([^，,。；;、）)]+)",
    r"招(?:一个|一名|一位|名|位|个)?[（(]?([^，,。；;、）)]+)",
    r"岗位[：:]\s*([^，,。；;]+)",
    r"职位[：:]\s*([^，,。；;]+)",
]


def _extract_title(text: str) -> str | None:
    for pat in _TITLE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    head = re.split(r"[，,。；;]", text, maxsplit=1)[0].strip()
    return head or None


async def parse_requirement(text: str) -> JDParsed:
    """一句话描述 → 结构化字段。原始需求保留在 requirements，不静默丢输入。"""
    return JDParsed(title=_extract_title(text), requirements=[text])


async def _resolve_title(request: JDGenerateRequest) -> str:
    """解析入口：仅一句话描述时先解析出标题。"""
    title = request.title
    if request.description and not title:
        parsed = await parse_requirement(request.description)
        title = parsed.title
    return title or "未命名岗位"


def _build_create(
    request: JDGenerateRequest,
    title: str,
    content: str,
    output: dict,
) -> JobDescriptionCreate:
    raw = request.description
    return JobDescriptionCreate(
        title=title,
        content=content,
        department=request.department or output.get("department"),
        location=request.location or output.get("location"),
        salary_range=request.salary_range or output.get("salary_range"),
        experience_level=request.experience_level or output.get("experience_level"),
        education=request.education or output.get("education"),
        job_type=request.job_type or output.get("job_type"),
        skills=request.skills or output.get("skills"),
        requirements=request.requirements or ([raw] if raw else output.get("requirements")),
    )


async def generate_jd(request: JDGenerateRequest) -> JobDescriptionCreate:
    """阻塞式生成 JD 初稿（不落库）。"""
    title = await _resolve_title(request)
    output = await dify_client.run_jd_workflow({})
    return _build_create(request, title, output.get("content", ""), output)


async def generate_jd_stream(request: JDGenerateRequest) -> AsyncIterator[dict]:
    """SSE 流式生成：thinking → delta* → final。final 携带完整结构化初稿。"""
    title = await _resolve_title(request)
    yield {"event": "thinking", "data": "正在生成 JD 初稿..."}
    chunks: list[str] = []
    async for chunk in dify_client.stream_jd_workflow({}):
        chunks.append(chunk)
        yield {"event": "delta", "data": chunk}
    content = "".join(chunks)
    final = _build_create(request, title, content, {})
    yield {"event": "final", "data": final.model_dump(mode="json")}


# ---------- CRUD 与状态机 ----------


async def list_jds(db: AsyncSession) -> list[JobDescription]:
    result = await db.execute(
        select(JobDescription).order_by(JobDescription.created_at.desc())
    )
    return list(result.scalars().all())


async def get_jd(jd_id: uuid.UUID, db: AsyncSession) -> JobDescription:
    jd = await db.get(JobDescription, jd_id)
    if jd is None:
        raise HTTPException(status_code=404, detail="JD 不存在")
    return jd


async def create_jd(
    schema: JobDescriptionCreate, user: User, db: AsyncSession
) -> JobDescription:
    jd = JobDescription(**schema.model_dump(), user_id=user.id, workflow_type="jd")
    db.add(jd)
    await db.flush()
    return jd


async def update_jd(
    jd_id: uuid.UUID, schema: JobDescriptionUpdate, db: AsyncSession
) -> JobDescription:
    jd = await get_jd(jd_id, db)
    for key, value in schema.model_dump(exclude_unset=True).items():
        setattr(jd, key, value)
    await db.flush()
    return jd


async def change_status(
    jd_id: uuid.UUID, status: str, db: AsyncSession
) -> JobDescription:
    if status not in JDStatus._value2member_map_:
        raise HTTPException(status_code=422, detail="非法 JD 状态")
    jd = await get_jd(jd_id, db)
    jd.status = status
    await db.flush()
    return jd


async def delete_jd(jd_id: uuid.UUID, db: AsyncSession) -> None:
    jd = await get_jd(jd_id, db)
    await db.delete(jd)
    await db.flush()
