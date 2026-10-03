"""L2 集成测试（doc 42 §7：24 道）——API 端点权限真门 + SSE 流式契约。

覆盖：招聘端点 8 + 知识端点 6 + 系统管理 5 + SSE 契约 5。
依赖 PostgreSQL 测试库（conftest 的 engine/db_session），标记 `@pytest.mark.l2`。
"""
import pytest

from app.core.security import create_access_token, get_password_hash
from app.evaluations import eval_utils as eu
from app.models import JobDescription, User

pytestmark = pytest.mark.l2


async def _make_user(db_session, username, role="employee", is_superuser=False):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("secret123"),
        role=role,
        is_superuser=is_superuser,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _auth(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(subject=username)}"}


async def _make_jd(db_session, title="前端开发工程师", content="负责前端开发"):
    jd = JobDescription(title=title, content=content)
    db_session.add(jd)
    await db_session.flush()
    return jd


# ---------- 招聘端点（8） ----------

async def test_employee_cannot_create_jd(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    resp = await client.post(
        "/api/v1/job-descriptions",
        json={"title": "岗位", "content": "正文"},
        headers=_auth("emp"),
    )
    assert resp.status_code == 403


async def test_hr_manager_create_and_read_jd(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    create = await client.post(
        "/api/v1/job-descriptions",
        json={"title": "岗位", "content": "正文"},
        headers=_auth("hr"),
    )
    assert create.status_code == 201
    got = await client.get(
        f"/api/v1/job-descriptions/{create.json()['id']}", headers=_auth("hr")
    )
    assert got.status_code == 200
    assert got.json()["title"] == "岗位"


async def test_jd_generate_returns_content(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    resp = await client.post(
        "/api/v1/job-descriptions/generate",
        json={"title": "前端开发工程师"},
        headers=_auth("hr"),
    )
    assert resp.status_code == 200
    assert resp.json()["content"]


async def test_scoring_generate_is_balanced(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    resp = await client.post(
        "/api/v1/scoring-criteria/generate",
        json={"job_title": "前端开发工程师", "content": "岗位职责与任职要求"},
        headers=_auth("hr"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_score"] == 100
    assert body["is_balanced"] is True


async def test_resume_evaluate_returns_metrics(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    jd = await _make_jd(db_session)
    resp = await client.post(
        "/api/v1/resume-evaluation/evaluate",
        json={"resume_content": "五年经验的前端工程师", "job_description_id": str(jd.id)},
        headers=_auth("hr"),
    )
    assert resp.status_code == 201
    assert resp.json()["total_score"] is not None
    assert len(resp.json()["evaluation_metrics"]) == 5


async def test_interview_plan_generate_flow(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    jd = await _make_jd(db_session)
    ev = await client.post(
        "/api/v1/resume-evaluation/evaluate",
        json={"resume_content": "五年经验的前端工程师", "job_description_id": str(jd.id)},
        headers=_auth("hr"),
    )
    plan = await client.post(
        "/api/v1/interview-plans/generate",
        json={"resume_evaluation_id": ev.json()["id"]},
        headers=_auth("hr"),
    )
    assert plan.status_code == 201
    assert plan.json()["content"]


async def test_jd_status_transition(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    jd = await _make_jd(db_session)
    resp = await client.patch(
        f"/api/v1/job-descriptions/{jd.id}/status",
        params={"status": "published"},
        headers=_auth("hr"),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


async def test_jd_delete(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    jd = await _make_jd(db_session)
    resp = await client.delete(f"/api/v1/job-descriptions/{jd.id}", headers=_auth("hr"))
    assert resp.status_code == 204


# ---------- 知识端点（6） ----------

async def test_kb_create_and_list(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    create = await client.post(
        "/api/v1/knowledge-base", json={"name": "企业制度库"}, headers=_auth("hr")
    )
    assert create.status_code == 201
    lst = await client.get("/api/v1/knowledge-base", headers=_auth("hr"))
    assert lst.status_code == 200
    assert any(k["name"] == "企业制度库" for k in lst.json())


async def test_employee_can_read_kb(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    await client.post("/api/v1/knowledge-base", json={"name": "企业制度库"}, headers=_auth("hr"))
    await _make_user(db_session, "emp", role="employee")
    resp = await client.get("/api/v1/knowledge-base", headers=_auth("emp"))
    assert resp.status_code == 200


async def test_employee_cannot_create_kb(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    resp = await client.post(
        "/api/v1/knowledge-base", json={"name": "库"}, headers=_auth("emp")
    )
    assert resp.status_code == 403


async def test_document_upload_and_list(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("考勤制度.txt", "员工每日上下班需打卡。".encode("utf-8"), "text/plain")},
        headers=_auth("hr"),
    )
    assert resp.status_code == 201
    lst = await client.get("/api/v1/documents", headers=_auth("hr"))
    assert lst.status_code == 200
    assert len(lst.json()) == 1


async def test_knowledge_assistant_ask(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    resp = await client.post(
        "/api/v1/knowledge-assistant/ask",
        json={"question": "公司考勤怎么打卡"},
        headers=_auth("hr"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] in ("KB", "GENERAL")
    assert "answer" in body


async def test_kb_delete(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    create = await client.post(
        "/api/v1/knowledge-base", json={"name": "待删库"}, headers=_auth("hr")
    )
    resp = await client.delete(
        f"/api/v1/knowledge-base/{create.json()['id']}", headers=_auth("hr")
    )
    assert resp.status_code == 204


# ---------- 系统管理（5） ----------

async def test_superuser_list_users(client, db_session):
    await _make_user(db_session, "root", role="admin", is_superuser=True)
    resp = await client.get("/api/v1/users", headers=_auth("root"))
    assert resp.status_code == 200


async def test_non_superuser_cannot_list_users(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    resp = await client.get("/api/v1/users", headers=_auth("hr"))
    assert resp.status_code == 403


async def test_superuser_create_user(client, db_session):
    await _make_user(db_session, "root", role="admin", is_superuser=True)
    resp = await client.post(
        "/api/v1/users",
        json={"username": "newbie", "email": "newbie@example.com", "password": "secret123"},
        headers=_auth("root"),
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "newbie"


async def test_superuser_list_roles(client, db_session):
    await _make_user(db_session, "root", role="admin", is_superuser=True)
    resp = await client.get("/api/v1/roles", headers=_auth("root"))
    assert resp.status_code == 200


async def test_stats_dashboard_admin_only(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    admin = await client.get("/api/v1/stats/dashboard", headers=_auth("hr"))
    assert admin.status_code == 200

    await _make_user(db_session, "emp", role="employee")
    emp = await client.get("/api/v1/stats/dashboard", headers=_auth("emp"))
    assert emp.status_code == 403


# ---------- SSE 流式契约（5） ----------

async def _stream_jd(client, username) -> tuple[str, str]:
    async with client.stream(
        "POST",
        "/api/v1/job-descriptions/generate-stream",
        json={"title": "前端开发工程师"},
        headers=_auth(username),
    ) as resp:
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk
        return resp.headers.get("content-type", ""), body


async def test_sse_content_type(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    ctype, _ = await _stream_jd(client, "hr")
    assert ctype.startswith("text/event-stream")


async def test_sse_emits_thinking_delta_final(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    _, body = await _stream_jd(client, "hr")
    assert "event: thinking" in body
    assert "event: delta" in body
    assert "event: final" in body


async def test_sse_event_frames_well_formed(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    _, body = await _stream_jd(client, "hr")
    # 每个事件帧为 event: X\n data: ...\n\n
    frames = [f for f in body.split("\n\n") if f.strip()]
    assert frames
    for frame in frames:
        assert frame.startswith("event: ")
        assert "\ndata: " in frame


async def test_sse_chat_contract_conformance(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    _, body = await _stream_jd(client, "hr")
    events = [ln.split("event: ")[1] for ln in body.splitlines() if ln.startswith("event: ")]
    # JD 生成流（doc 33）：thinking → delta… → final，事件类型须在契约枚举内
    known = (*eu.SSE_CHAT_EVENTS, *eu.SSE_TASK_EVENTS, eu.SSE_ERROR_EVENT)
    assert events[0] == "thinking"
    assert events[-1] == "final"
    assert "delta" in events
    assert all(e in known for e in events)


async def test_sse_requires_admin(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    resp = await client.post(
        "/api/v1/job-descriptions/generate-stream",
        json={"title": "前端开发工程师"},
        headers=_auth("emp"),
    )
    assert resp.status_code == 403
