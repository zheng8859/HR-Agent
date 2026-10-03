"""面试方案端点测试：RBAC、守卫、导出 BOM 编码、所有权。"""
import uuid

from app.core.security import create_access_token, get_password_hash
from app.models import JobDescription, ResumeEvaluation, ResumeEvaluationStatus, User
from app.services import interview_plan_service as svc


async def _make_user(db_session, username="hr", role="hr_manager"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("secret123"),
        role=role,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_jd(db_session):
    jd = JobDescription(title="前端开发工程师", content="负责前端页面开发")
    db_session.add(jd)
    await db_session.flush()
    return jd


async def _make_evaluation(db_session, user, jd, name="张三", total_score=78.0):
    ev = ResumeEvaluation(
        candidate_name=name,
        candidate_position="前端开发工程师",
        resume_content="五年前端经验，精通 Vue/TypeScript",
        total_score=total_score,
        evaluation_metrics=[{"name": "学历匹配度", "score": 16, "max": 20, "reason": "本科"}],
        status=ResumeEvaluationStatus.pending.value,
        job_description_id=jd.id,
        user_id=user.id,
    )
    db_session.add(ev)
    await db_session.flush()
    return ev


def _auth(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(subject=username)}"}


async def test_employee_cannot_generate(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    resp = await client.post(
        "/api/v1/interview-plans/generate",
        json={"resume_evaluation_id": str(uuid.uuid4())},
        headers=_auth("emp"),
    )
    assert resp.status_code == 403


async def test_generate_unscored_returns_422(client, db_session):
    hr = await _make_user(db_session, "hr")
    jd = await _make_jd(db_session)
    ev = await _make_evaluation(db_session, hr, jd, total_score=None)
    resp = await client.post(
        "/api/v1/interview-plans/generate",
        json={"resume_evaluation_id": str(ev.id)},
        headers=_auth("hr"),
    )
    assert resp.status_code == 422


async def test_generate_export_flow(client, db_session):
    hr = await _make_user(db_session, "hr")
    jd = await _make_jd(db_session)
    ev = await _make_evaluation(db_session, hr, jd)

    resp = await client.post(
        "/api/v1/interview-plans/generate",
        json={"resume_evaluation_id": str(ev.id)},
        headers=_auth("hr"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["resume_evaluation_id"] == str(ev.id)
    for header in svc.INTERVIEW_SECTION_TITLES:
        assert header in body["content"]

    export = await client.get(
        f"/api/v1/interview-plans/{body['id']}/export",
        params={"format": "md"},
        headers=_auth("hr"),
    )
    assert export.status_code == 200
    assert export.text.startswith("﻿")
    for header in svc.INTERVIEW_SECTION_TITLES:
        assert header in export.text


async def test_ownership_other_user_cannot_read(client, db_session):
    hr = await _make_user(db_session, "hr")
    hr2 = await _make_user(db_session, "hr2")
    jd = await _make_jd(db_session)
    ev = await _make_evaluation(db_session, hr, jd)

    resp = await client.post(
        "/api/v1/interview-plans/generate",
        json={"resume_evaluation_id": str(ev.id)},
        headers=_auth("hr"),
    )
    pid = resp.json()["id"]

    got = await client.get(f"/api/v1/interview-plans/{pid}", headers=_auth("hr2"))
    assert got.status_code == 404

    lst = await client.get("/api/v1/interview-plans", headers=_auth("hr2"))
    assert lst.json() == []
