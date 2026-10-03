"""简历评估服务单元测试：上传校验、文本提取、五维度解析、总分=维度之和、状态流转、所有权、导出。"""
import io
import uuid

import pytest
from fastapi import HTTPException

from app.models import JobDescription, ResumeEvaluationStatus, User
from app.schemas.resume_evaluation import (
    ResumeAutoEvaluateRequest,
    ResumeEvaluateRequest,
)
from app.services import resume_evaluation_service as svc


# ---------- 文本提取辅助 ----------


def _make_docx(text: str) -> bytes:
    import docx

    d = docx.Document()
    d.add_paragraph(text)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _make_pdf(text: str) -> bytes:
    """构造一个含文本层的最小合法 PDF（用于 pdfplumber 提取测试）。"""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF".encode()
    )
    return bytes(out)


async def _make_user(db_session, username="hr", role="hr_manager"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="x",
        role=role,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ---------- 上传校验 ----------


def test_validate_upload_rejects_bad_extension():
    with pytest.raises(HTTPException) as e:
        svc.validate_upload("resume.txt", 100)
    assert e.value.status_code == 422


def test_validate_upload_rejects_oversize():
    with pytest.raises(HTTPException) as e:
        svc.validate_upload("resume.pdf", 11 * 1024 * 1024)
    assert e.value.status_code == 422


def test_validate_upload_accepts_pdf_uppercase():
    assert svc.validate_upload("Resume.PDF", 1024) == "pdf"


def test_validate_upload_accepts_docx():
    assert svc.validate_upload("resume.docx", 1024) == "docx"


# ---------- 文本提取 ----------


def test_extract_docx_text():
    text = svc.extract_text("docx", _make_docx("张三 前端工程师 五年经验"))
    assert "张三" in text


def test_extract_pdf_text():
    text = svc.extract_text("pdf", _make_pdf("Hello Resume"))
    assert "Hello" in text


def test_extract_empty_content_raises():
    with pytest.raises(HTTPException) as e:
        svc.extract_text("pdf", b"")
    assert e.value.status_code == 422


# ---------- 维度解析 ----------


def test_parse_dimensions_total_is_sum_of_scores():
    output = {
        "total_score": 999,  # 故意不配平，应以维度之和为准
        "dimensions": [
            {"name": "学历匹配度", "score": 16, "max": 20, "reason": "本科学历"},
            {"name": "工作经验", "score": 20, "max": 25, "reason": "五年经验"},
            {"name": "技能匹配度", "score": 22, "max": 25, "reason": "技能匹配"},
            {"name": "项目经验匹配度", "score": 14, "max": 20, "reason": "项目相关"},
            {"name": "综合素质", "score": 6, "max": 10, "reason": "沟通良好"},
        ],
    }
    dims, total = svc.parse_dimensions(output)
    assert total == 78  # 16+20+22+14+6，不虚构 999
    assert len(dims) == 5
    for d in dims:
        assert d.reason  # 评分必须带理由


# ---------- 评估（异步，需 DB） ----------


async def test_evaluate_creates_record_with_five_dimensions(db_session):
    user = await _make_user(db_session)
    jd = JobDescription(title="前端开发工程师", content="JD")
    db_session.add(jd)
    await db_session.flush()

    rec = await svc.evaluate(
        ResumeEvaluateRequest(resume_content="张三的简历", job_description_id=jd.id),
        user,
        db_session,
    )
    assert rec.total_score is not None
    assert len(rec.evaluation_metrics) == 5
    assert rec.status == ResumeEvaluationStatus.pending.value
    assert rec.user_id == user.id
    assert rec.job_description_id == jd.id


async def test_evaluate_missing_jd_404(db_session):
    user = await _make_user(db_session)
    with pytest.raises(HTTPException) as e:
        await svc.evaluate(
            ResumeEvaluateRequest(resume_content="x", job_description_id=uuid.uuid4()),
            user,
            db_session,
        )
    assert e.value.status_code == 404


async def test_evaluate_auto_matches_existing_jd(db_session):
    user = await _make_user(db_session)
    jd = JobDescription(title="前端开发工程师", content="JD")
    db_session.add(jd)
    await db_session.flush()

    rec = await svc.evaluate_auto(
        ResumeAutoEvaluateRequest(resume_content="前端开发工程师 五年经验"),
        user,
        db_session,
    )
    assert rec.job_description_id == jd.id


async def test_update_status_flow(db_session):
    user = await _make_user(db_session)
    jd = JobDescription(title="岗位", content="JD")
    db_session.add(jd)
    await db_session.flush()
    rec = await svc.evaluate(
        ResumeEvaluateRequest(resume_content="简历", job_description_id=jd.id),
        user,
        db_session,
    )

    updated = await svc.update_status(rec.id, "interview", user, db_session)
    assert updated.status == "interview"

    with pytest.raises(HTTPException) as e:
        await svc.update_status(rec.id, "bogus", user, db_session)
    assert e.value.status_code == 422


async def test_ownership_isolation(db_session):
    owner = await _make_user(db_session, "owner")
    other = await _make_user(db_session, "other")
    jd = JobDescription(title="岗位", content="JD")
    db_session.add(jd)
    await db_session.flush()

    rec = await svc.evaluate(
        ResumeEvaluateRequest(resume_content="简历", job_description_id=jd.id),
        owner,
        db_session,
    )

    # 他人不可见
    with pytest.raises(HTTPException) as e:
        await svc.get_evaluation(rec.id, other, db_session)
    assert e.value.status_code == 404

    assert len(await svc.list_evaluations(other, db_session)) == 0
    assert len(await svc.list_evaluations(owner, db_session)) == 1


async def test_export_contains_dimensions_and_reasons(db_session):
    user = await _make_user(db_session)
    jd = JobDescription(title="岗位", content="JD")
    db_session.add(jd)
    await db_session.flush()
    rec = await svc.evaluate(
        ResumeEvaluateRequest(resume_content="简历", job_description_id=jd.id),
        user,
        db_session,
    )

    export = await svc.export_evaluation(rec.id, user, db_session)
    assert export.total_score == rec.total_score
    assert len(export.dimensions) == 5
    assert export.text
