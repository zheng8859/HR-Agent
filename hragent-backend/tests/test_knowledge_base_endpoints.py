"""知识库端点测试：RBAC、CRUD、名称唯一、含文档删除 409。"""
import uuid

from app.core.security import create_access_token, get_password_hash
from app.models import Document, DocumentStatus, KnowledgeBase, User


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


def _auth(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(subject=username)}"}


async def test_employee_cannot_create(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    resp = await client.post(
        "/api/v1/knowledge-base", json={"name": "员工手册"}, headers=_auth("emp")
    )
    assert resp.status_code == 403


async def test_create_and_list(client, db_session):
    await _make_user(db_session, "hr")
    resp = await client.post(
        "/api/v1/knowledge-base",
        json={"name": "员工手册", "description": "入职指南"},
        headers=_auth("hr"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "员工手册"

    lst = await client.get("/api/v1/knowledge-base", headers=_auth("hr"))
    assert any(k["name"] == "员工手册" for k in lst.json())


async def test_create_duplicate_409(client, db_session):
    await _make_user(db_session, "hr")
    await _make_kb(db_session, "员工手册")
    resp = await client.post(
        "/api/v1/knowledge-base", json={"name": "员工手册"}, headers=_auth("hr")
    )
    assert resp.status_code == 409


async def test_update_and_get(client, db_session):
    await _make_user(db_session, "hr")
    kb = await _make_kb(db_session, "旧名")
    resp = await client.put(
        f"/api/v1/knowledge-base/{kb.id}",
        json={"name": "新名"},
        headers=_auth("hr"),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名"

    got = await client.get(f"/api/v1/knowledge-base/{kb.id}", headers=_auth("hr"))
    assert got.status_code == 200
    assert got.json()["name"] == "新名"


async def test_delete_with_documents_409(client, db_session):
    hr = await _make_user(db_session, "hr")
    kb = await _make_kb(db_session)
    doc = Document(
        filename="a.txt",
        original_filename="a.txt",
        status=DocumentStatus.processed.value,
        chunk_count=1,
        user_id=hr.id,
        knowledge_base_id=kb.id,
    )
    db_session.add(doc)
    await db_session.flush()

    resp = await client.delete(f"/api/v1/knowledge-base/{kb.id}", headers=_auth("hr"))
    assert resp.status_code == 409


async def test_delete_empty_kb(client, db_session):
    await _make_user(db_session, "hr")
    kb = await _make_kb(db_session)
    resp = await client.delete(f"/api/v1/knowledge-base/{kb.id}", headers=_auth("hr"))
    assert resp.status_code == 204
