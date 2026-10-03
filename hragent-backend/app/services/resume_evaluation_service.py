"""简历评估服务：文件校验/文本提取、五维度打分（总分=维度之和）、状态流转、所有权隔离。

设计要点（doc 15 §2.3 + doc 37）：
- 上传仅限 PDF/DOC/DOCX，默认 ≤10MB，服务端强制（`validate_upload`）。
- 评分「可解释才可信」：每个维度带 score/max/reason，total 一律由维度之和推算，不虚构 Dify 返回的总分。
- 简历属敏感个人信息，list/get 仅返回本人（`user_id` 过滤），他人 404。
- 状态 pending/rejected/interview 由 HR 手动流转，AI 不决定去留。
"""
from __future__ import annotations

import io
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    JobDescription,
    ResumeEvaluation,
    ResumeEvaluationStatus,
    ScoringCriteria,
    User,
)
from app.schemas.resume_evaluation import (
    ResumeAutoEvaluateRequest,
    ResumeDimension,
    ResumeEvaluateRequest,
    ResumeExport,
    ResumeUploadResult,
)
from app.services.dify_service import dify_client


# ---------- 上传校验与文本提取 ----------


def validate_upload(filename: str, size: int) -> str:
    """校验扩展名与大小，返回规范化小写扩展名；不合法抛 422。"""
    if "." not in filename:
        raise HTTPException(status_code=422, detail="不支持的文件格式")
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = [t.strip().lower() for t in settings.resume_allowed_types.split(",")]
    if ext not in allowed:
        raise HTTPException(status_code=422, detail=f"不支持的文件格式：{ext}")
    max_bytes = settings.resume_max_size_mb * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"文件大小超过限制（{settings.resume_max_size_mb}MB）",
        )
    return ext


def _extract_pdf(content: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def _extract_docx(content: bytes) -> str:
    import docx

    d = docx.Document(io.BytesIO(content))
    return "\n".join(p.text for p in d.paragraphs)


def extract_text(file_type: str, content: bytes) -> str:
    """按文件类型提取纯文本；内容为空或解析失败抛 422。"""
    if not content or not content.strip():
        raise HTTPException(status_code=422, detail="无法从简历中提取文本内容")
    try:
        if file_type == "pdf":
            text = _extract_pdf(content)
        elif file_type == "docx":
            text = _extract_docx(content)
        elif file_type == "doc":
            # 旧版 .doc 二进制无法用 python-docx 解析，退化为文本解码
            try:
                text = _extract_docx(content)
            except Exception:
                text = content.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(status_code=422, detail=f"不支持的文件格式：{file_type}")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="无法从简历中提取文本内容") from None

    if not text or not text.strip():
        raise HTTPException(status_code=422, detail="无法从简历中提取文本内容")
    return text.strip()


async def upload_resume(file: UploadFile, _user: User) -> ResumeUploadResult:
    """读取上传文件并抽取文本（尚未评估）。"""
    content = await file.read()
    file_type = validate_upload(file.filename or "", len(content))
    text = extract_text(file_type, content)
    return ResumeUploadResult(
        original_filename=file.filename or "",
        file_type=file_type,
        resume_content=text,
    )


# ---------- 维度解析 ----------


def parse_dimensions(output: dict) -> tuple[list[ResumeDimension], float]:
    """解析 Dify 输出为维度列表 + 总分。总分 = 维度得分之和，不信任返回的 total_score。"""
    raw_dims = output.get("dimensions") or []
    dims = [ResumeDimension(**d) for d in raw_dims]
    if not dims:
        raise HTTPException(status_code=502, detail="简历评估解析失败：缺少评分维度")
    total = round(sum(d.score for d in dims), 2)
    return dims, total


# ---------- 评估 ----------


async def _evaluate(
    resume_content: str,
    scoring_criteria_id: uuid.UUID | None,
    original_filename: str | None,
    file_type: str | None,
    jd: JobDescription,
    user: User,
    db: AsyncSession,
) -> ResumeEvaluation:
    output = await dify_client.run_resume_workflow(
        {
            "resume_content": resume_content,
            "job_title": jd.title or "",
            "job_content": jd.content or "",
        }
    )
    dims, total = parse_dimensions(output)
    rec = ResumeEvaluation(
        original_filename=original_filename,
        file_type=file_type,
        resume_content=resume_content,
        candidate_name=output.get("candidate_name"),
        candidate_position=output.get("candidate_position"),
        work_years=output.get("work_years"),
        education_level=output.get("education_level"),
        school=output.get("school"),
        total_score=total,
        evaluation_metrics=[d.model_dump() for d in dims],
        status=ResumeEvaluationStatus.pending.value,
        job_description_id=jd.id,
        scoring_criteria_id=scoring_criteria_id,
        user_id=user.id,
    )
    db.add(rec)
    await db.flush()
    return rec


async def evaluate(
    request: ResumeEvaluateRequest, user: User, db: AsyncSession
) -> ResumeEvaluation:
    """绑定指定 JD 评估简历。JD/评分标准不存在则 404。"""
    jd = await db.get(JobDescription, request.job_description_id)
    if jd is None:
        raise HTTPException(status_code=404, detail="绑定的 JD 不存在")
    if request.scoring_criteria_id is not None:
        sc = await db.get(ScoringCriteria, request.scoring_criteria_id)
        if sc is None:
            raise HTTPException(status_code=404, detail="绑定的评分标准不存在")
    return await _evaluate(
        request.resume_content,
        request.scoring_criteria_id,
        request.original_filename,
        request.file_type,
        jd,
        user,
        db,
    )


async def evaluate_auto(
    request: ResumeAutoEvaluateRequest, user: User, db: AsyncSession
) -> ResumeEvaluation:
    """不指定 JD：优先按岗位名匹配简历内容，否则取最新 JD。"""
    result = await db.execute(
        select(JobDescription).order_by(JobDescription.created_at.desc())
    )
    jds = list(result.scalars().all())
    jd = next((c for c in jds if c.title and c.title in request.resume_content), None)
    if jd is None and jds:
        jd = jds[0]
    if jd is None:
        raise HTTPException(status_code=404, detail="暂无可用 JD，无法自动匹配")
    return await _evaluate(
        request.resume_content,
        request.scoring_criteria_id,
        request.original_filename,
        request.file_type,
        jd,
        user,
        db,
    )


# ---------- 查询 / 状态 / 导出（所有权：仅本人） ----------


async def list_evaluations(user: User, db: AsyncSession) -> list[ResumeEvaluation]:
    result = await db.execute(
        select(ResumeEvaluation)
        .where(ResumeEvaluation.user_id == user.id)
        .order_by(ResumeEvaluation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_evaluation(
    evaluation_id: uuid.UUID, user: User, db: AsyncSession
) -> ResumeEvaluation:
    rec = await db.get(ResumeEvaluation, evaluation_id)
    if rec is None or rec.user_id != user.id:
        raise HTTPException(status_code=404, detail="简历评估不存在")
    return rec


async def update_status(
    evaluation_id: uuid.UUID, status: str, user: User, db: AsyncSession
) -> ResumeEvaluation:
    if status not in ResumeEvaluationStatus._value2member_map_:
        raise HTTPException(status_code=422, detail="非法简历状态")
    rec = await get_evaluation(evaluation_id, user, db)
    rec.status = status
    await db.flush()
    # updated_at 带 onupdate=now()，UPDATE 后属性过期；刷新避免响应序列化时触发惰性 IO（MissingGreenlet）
    await db.refresh(rec)
    return rec


async def export_evaluation(
    evaluation_id: uuid.UUID, user: User, db: AsyncSession
) -> ResumeExport:
    rec = await get_evaluation(evaluation_id, user, db)
    dims = [ResumeDimension(**m) for m in (rec.evaluation_metrics or [])]
    return ResumeExport(
        candidate_name=rec.candidate_name,
        candidate_position=rec.candidate_position,
        total_score=rec.total_score,
        dimensions=dims,
        status=rec.status,
        text=rec.resume_content or "",
    )
