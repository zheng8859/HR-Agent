"""简历评估端点测试：RBAC 权限真门 + 上传校验 + 数据依赖 + 所有权。"""
from app.core.security import create_access_token, get_password_hash
from app.models import JobDescription, User


async def _make_user(db_session, username, role="employee"):
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


def _auth(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(subject=username)}"}


async def test_employee_cannot_evaluate(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    jd = JobDescription(title="岗位", content="正文")
    db_session.add(jd)
    await db_session.flush()
    resp = await client.post(
        "/api/v1/resume-evaluation/evaluate",
        json={"resume_content": "x", "job_description_id": str(jd.id)},
        headers=_auth("emp"),
    )
    assert resp.status_code == 403


async def test_upload_rejects_bad_type(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    resp = await client.post(
        "/api/v1/resume-evaluation/upload",
        files={"file": ("resume.txt", b"hello", "text/plain")},
        headers=_auth("hr"),
    )
    assert resp.status_code == 422


async def test_hr_evaluate_status_export_flow(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    jd = JobDescription(title="前端开发工程师", content="正文")
    db_session.add(jd)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/resume-evaluation/evaluate",
        json={"resume_content": "简历", "job_description_id": str(jd.id)},
        headers=_auth("hr"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_score"] is not None
    assert len(body["evaluation_metrics"]) == 5

    lst = await client.get("/api/v1/resume-evaluation", headers=_auth("hr"))
    assert lst.status_code == 200
    assert len(lst.json()) == 1

    upd = await client.patch(
        f"/api/v1/resume-evaluation/{body['id']}/status",
        params={"status": "interview"},
        headers=_auth("hr"),
    )
    assert upd.status_code == 200
    assert upd.json()["status"] == "interview"

    exp = await client.get(
        f"/api/v1/resume-evaluation/{body['id']}/export", headers=_auth("hr")
    )
    assert exp.status_code == 200
    assert exp.json()["total_score"] == body["total_score"]


async def test_ownership_other_user_cannot_read(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    await _make_user(db_session, "hr2", role="hr_manager")
    jd = JobDescription(title="前端", content="正文")
    db_session.add(jd)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/resume-evaluation/evaluate",
        json={"resume_content": "简历", "job_description_id": str(jd.id)},
        headers=_auth("hr"),
    )
    eid = resp.json()["id"]

    got = await client.get(f"/api/v1/resume-evaluation/{eid}", headers=_auth("hr2"))
    assert got.status_code == 404

    lst = await client.get("/api/v1/resume-evaluation", headers=_auth("hr2"))
    assert lst.json() == []
