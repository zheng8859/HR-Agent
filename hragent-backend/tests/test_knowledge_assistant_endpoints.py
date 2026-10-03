"""知识问答端点测试：RBAC、闲聊/有依据/无依据三态、用户隔离。"""
from app.core.security import create_access_token, get_password_hash
from app.models import Document, DocumentStatus, KnowledgeBase, User
from app.services.embedding_service import embed_text


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


async def _make_kb(db_session, name="企业制度库"):
    kb = KnowledgeBase(name=name, description="测试", document_count=0)
    db_session.add(kb)
    await db_session.flush()
    return kb


async def _make_doc(db_session, user, kb, filename, content):
    doc = Document(
        filename=filename,
        original_filename=filename,
        status=DocumentStatus.processed.value,
        chunk_count=1,
        extracted_content=content,
        embedding=embed_text(content),
        user_id=user.id,
        knowledge_base_id=kb.id,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


def _auth(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(subject=username)}"}


async def test_requires_auth(client):
    resp = await client.post("/api/v1/knowledge-assistant/ask", json={"question": "年假"})
    assert resp.status_code == 401


async def test_chitchat_returns_general(client, db_session):
    await _make_user(db_session, "hr")
    resp = await client.post(
        "/api/v1/knowledge-assistant/ask",
        json={"question": "你好"},
        headers=_auth("hr"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "GENERAL"
    assert body["document_chunks"] == []


async def test_kb_question_returns_answer_and_sources(client, db_session):
    hr = await _make_user(db_session, "hr")
    kb = await _make_kb(db_session)
    await _make_doc(
        db_session, hr, kb, "差旅管理办法.pdf",
        "一线城市出差住宿标准为500元每间每晚。",
    )
    resp = await client.post(
        "/api/v1/knowledge-assistant/ask",
        json={"question": "出差住宿标准"},
        headers=_auth("hr"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answered"] is True
    assert body["answer"]
    assert len(body["document_chunks"]) >= 1
    assert body["confidence"] >= 0.2


async def test_no_match_returns_insufficient(client, db_session):
    hr = await _make_user(db_session, "hr")
    kb = await _make_kb(db_session)
    await _make_doc(db_session, hr, kb, "年假规则.pdf", "员工入职满一年可享五天年假。")
    resp = await client.post(
        "/api/v1/knowledge-assistant/ask",
        json={"question": "商业健康意外险理赔周期"},
        headers=_auth("hr"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answered"] is False
    assert "资料不足" in body["answer"]


async def test_cross_user_isolation(client, db_session):
    hr = await _make_user(db_session, "hr")
    kb = await _make_kb(db_session)
    await _make_doc(
        db_session, hr, kb, "差旅管理办法.pdf",
        "一线城市出差住宿标准为500元每间每晚。",
    )
    await _make_user(db_session, "hr2")
    resp = await client.post(
        "/api/v1/knowledge-assistant/ask",
        json={"question": "出差住宿标准"},
        headers=_auth("hr2"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answered"] is False  # 他人文档不可检索
