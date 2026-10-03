"""Agent 端点测试（doc 43）：intent / chat(SSE) / agent(SSE) / conversations + 认证真门。"""
import pytest

from app.core.security import create_access_token, get_password_hash
from app.models import User

pytestmark = pytest.mark.l2


async def _make_user(db_session, username, role="hr_manager"):
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


def _events(body: str) -> list[str]:
    return [ln.split("event: ")[1] for ln in body.splitlines() if ln.startswith("event: ")]


async def test_intent_endpoint(client, db_session):
    await _make_user(db_session, "hr")
    resp = await client.post(
        "/api/v1/intent", json={"message": "生成一份 JD"}, headers=_auth("hr")
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "jd"
    assert body["route"] == "recruitment.jd"
    assert body["source"] == "fast"


async def test_intent_requires_auth(client):
    resp = await client.post("/api/v1/intent", json={"message": "你好"})
    assert resp.status_code == 401


async def test_chat_sse_dialogue_sequence(client, db_session):
    await _make_user(db_session, "hr")
    async with client.stream(
        "POST", "/api/v1/chat", json={"message": "你好"}, headers=_auth("hr")
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/event-stream")
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk
    events = _events(body)
    assert events[0] == "thinking"
    assert "plan" in events
    assert "delta" in events
    assert events[-1] == "final"


async def test_agent_sse_task_sequence(client, db_session):
    await _make_user(db_session, "hr")
    async with client.stream(
        "POST", "/api/v1/agent", json={"message": "生成前端工程师 JD"}, headers=_auth("hr")
    ) as resp:
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk
    events = _events(body)
    assert events[0] == "progress"
    assert "artifact" in events
    assert events[-1] == "final"


async def test_chat_creates_conversation(client, db_session):
    await _make_user(db_session, "hr")
    async with client.stream(
        "POST", "/api/v1/chat", json={"message": "你好"}, headers=_auth("hr")
    ) as resp:
        async for _ in resp.aiter_text():
            pass
    lst = await client.get("/api/v1/conversations", headers=_auth("hr"))
    assert len(lst.json()) == 1


async def test_conversations_crud(client, db_session):
    await _make_user(db_session, "hr")
    create = await client.post(
        "/api/v1/conversations", json={"title": "会话"}, headers=_auth("hr")
    )
    assert create.status_code == 201
    cid = create.json()["id"]

    lst = await client.get("/api/v1/conversations", headers=_auth("hr"))
    assert any(c["id"] == cid for c in lst.json())

    detail = await client.get(f"/api/v1/conversations/{cid}", headers=_auth("hr"))
    assert detail.status_code == 200

    await client.delete(f"/api/v1/conversations/{cid}", headers=_auth("hr"))
    lst2 = await client.get("/api/v1/conversations", headers=_auth("hr"))
    assert all(c["id"] != cid for c in lst2.json())


async def test_feedback_endpoint(client, db_session):
    await _make_user(db_session, "hr")
    async with client.stream(
        "POST", "/api/v1/chat", json={"message": "你好"}, headers=_auth("hr")
    ) as resp:
        async for _ in resp.aiter_text():
            pass
    detail = await client.get("/api/v1/conversations", headers=_auth("hr"))
    cid = detail.json()[0]["id"]
    cd = await client.get(f"/api/v1/conversations/{cid}", headers=_auth("hr"))
    mid = cd.json()["messages"][1]["id"]

    fb = await client.post(
        "/api/v1/chat/feedback", json={"message_id": mid, "score": 5}, headers=_auth("hr")
    )
    assert fb.status_code == 200
    assert fb.json()["feedback_score"] == 5
