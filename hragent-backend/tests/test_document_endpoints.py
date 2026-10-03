"""文档端点测试：RBAC、上传校验、状态机、切片、隔离、重新处理。"""
import hashlib
import uuid

from app.core.config import settings
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


async def test_employee_cannot_upload(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    await _make_user(db_session, "emp", role="employee")
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("a.txt", b"hello", "text/plain")},
        headers=_auth("emp"),
    )
    assert resp.status_code == 403


async def test_upload_bad_format_422(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    await _make_user(db_session, "hr")
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("a.exe", b"MZ...", "application/octet-stream")},
        headers=_auth("hr"),
    )
    assert resp.status_code == 422


async def test_upload_process_and_chunks(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    hr = await _make_user(db_session, "hr")
    kb = await _make_kb(db_session)
    content = "第一段内容，用于测试上传与处理。".encode("utf-8")

    resp = await client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": str(kb.id)},
        files={"file": ("note.txt", content, "text/plain")},
        headers=_auth("hr"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == DocumentStatus.processed.value
    assert body["chunk_count"] >= 1
    assert body["file_hash"] == hashlib.sha256(content).hexdigest()
    assert body["knowledge_base_id"] == str(kb.id)

    doc_id = body["id"]
    chunks = await client.get(f"/api/v1/documents/{doc_id}/chunks", headers=_auth("hr"))
    assert chunks.status_code == 200
    assert len(chunks.json()["chunks"]) >= 1

    detail = await client.get(f"/api/v1/documents/{doc_id}", headers=_auth("hr"))
    assert detail.status_code == 200
    assert detail.json()["status"] == DocumentStatus.processed.value


async def test_upload_isolation(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    hr = await _make_user(db_session, "hr")
    hr2 = await _make_user(db_session, "hr2")
    kb = await _make_kb(db_session)

    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("a.txt", b"hello", "text/plain")},
        headers=_auth("hr"),
    )
    doc_id = resp.json()["id"]

    got = await client.get(f"/api/v1/documents/{doc_id}", headers=_auth("hr2"))
    assert got.status_code == 404
    lst = await client.get("/api/v1/documents", headers=_auth("hr2"))
    assert lst.json() == []
    lst_hr = await client.get("/api/v1/documents", headers=_auth("hr"))
    assert len(lst_hr.json()) == 1


async def test_reprocess_and_delete(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    hr = await _make_user(db_session, "hr")
    kb = await _make_kb(db_session)

    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("a.txt", b"hello world", "text/plain")},
        headers=_auth("hr"),
    )
    doc_id = resp.json()["id"]

    reprocess = await client.post(
        f"/api/v1/documents/{doc_id}/reprocess", headers=_auth("hr")
    )
    assert reprocess.status_code == 200
    assert reprocess.json()["status"] == DocumentStatus.processed.value

    deleted = await client.delete(f"/api/v1/documents/{doc_id}", headers=_auth("hr"))
    assert deleted.status_code == 204
    gone = await client.get(f"/api/v1/documents/{doc_id}", headers=_auth("hr"))
    assert gone.status_code == 404


async def test_delete_other_user_forbidden(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    hr = await _make_user(db_session, "hr")
    hr2 = await _make_user(db_session, "hr2")
    kb = await _make_kb(db_session)

    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("a.txt", b"hello", "text/plain")},
        headers=_auth("hr"),
    )
    doc_id = resp.json()["id"]
    deleted = await client.delete(f"/api/v1/documents/{doc_id}", headers=_auth("hr2"))
    assert deleted.status_code == 404
