"""招聘端点测试：后端权限真门（读/写分离）+ CRUD 端到端。"""
from app.core.security import create_access_token, get_password_hash
from app.models import User


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


async def test_employee_cannot_create_jd(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    resp = await client.post(
        "/api/v1/job-descriptions",
        json={"title": "岗位", "content": "正文"},
        headers=_auth("emp"),
    )
    assert resp.status_code == 403


async def test_employee_can_read_jds(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    resp = await client.get("/api/v1/job-descriptions", headers=_auth("emp"))
    assert resp.status_code == 200


async def test_hr_manager_can_create_and_read_jd(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    create = await client.post(
        "/api/v1/job-descriptions",
        json={"title": "岗位", "content": "正文"},
        headers=_auth("hr"),
    )
    assert create.status_code == 201
    jd_id = create.json()["id"]

    resp = await client.get(f"/api/v1/job-descriptions/{jd_id}", headers=_auth("hr"))
    assert resp.status_code == 200
    assert resp.json()["title"] == "岗位"


async def test_employee_cannot_create_scoring(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    resp = await client.post(
        "/api/v1/scoring-criteria",
        json={"title": "评分标准", "content": "正文"},
        headers=_auth("emp"),
    )
    assert resp.status_code == 403


async def test_hr_manager_generate_jd_and_scoring(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    jd = await client.post(
        "/api/v1/job-descriptions/generate",
        json={"title": "前端开发工程师"},
        headers=_auth("hr"),
    )
    assert jd.status_code == 200
    assert jd.json()["content"]

    scoring = await client.post(
        "/api/v1/scoring-criteria/generate",
        json={"job_title": "前端开发工程师", "content": jd.json()["content"]},
        headers=_auth("hr"),
    )
    assert scoring.status_code == 200
    body = scoring.json()
    assert body["total_score"] == 100
    assert body["is_balanced"] is True


async def test_jd_generate_stream_returns_sse(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    async with client.stream(
        "POST",
        "/api/v1/job-descriptions/generate-stream",
        json={"title": "前端开发工程师"},
        headers=_auth("hr"),
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk
    assert "event: thinking" in body
    assert "event: delta" in body
    assert "event: final" in body
