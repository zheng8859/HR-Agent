"""文档处理服务单元测试：哈希、校验、提取、切片、向量化、状态机、删除级联、所有权。"""
import hashlib

import pytest
from fastapi import HTTPException

from sqlalchemy import select

from app.core.config import settings
from app.models import Document, DocumentChunk, DocumentStatus, KnowledgeBase, User
from app.services import enhanced_document_service as svc
from app.services.embedding_service import embed_text


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


async def _make_kb(db_session, name="企业制度库"):
    kb = KnowledgeBase(name=name, description="测试知识库", document_count=0)
    db_session.add(kb)
    await db_session.flush()
    return kb


async def _make_doc(db_session, user, kb, status=DocumentStatus.uploaded.value):
    doc = Document(
        filename="test.txt",
        original_filename="test.txt",
        file_path="uploads/test.txt",
        file_size=10,
        file_hash="abc",
        mime_type="text/plain",
        status=status,
        chunk_count=0,
        user_id=user.id,
        knowledge_base_id=kb.id,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


# ---------- 哈希与校验 ----------


def test_compute_sha256():
    assert svc.compute_sha256(b"abc") == hashlib.sha256(b"abc").hexdigest()


def test_validate_document_bad_ext():
    with pytest.raises(HTTPException) as e:
        svc.validate_document("a.exe", 100)
    assert e.value.status_code == 422


def test_validate_document_oversize():
    with pytest.raises(HTTPException) as e:
        svc.validate_document("a.pdf", (settings.document_max_size_mb + 1) * 1024 * 1024)
    assert e.value.status_code == 422


def test_validate_document_ok():
    assert svc.validate_document("a.PDF", 100) == "pdf"
    assert svc.validate_document("a.txt", 100) == "txt"


# ---------- 提取 ----------


def test_extract_text_txt():
    assert svc.extract_text("txt", "  你好，世界  ".encode("utf-8")) == "你好，世界"


def test_extract_text_empty_raises():
    with pytest.raises(svc.ExtractionError):
        svc.extract_text("txt", b"")


# ---------- 语义切片 ----------


def test_chunk_text_empty():
    assert svc.chunk_text("") == []
    assert svc.chunk_text(None) == []


def test_chunk_text_short_single():
    assert svc.chunk_text("一段短文本") == ["一段短文本"]


def test_chunk_text_force_split_long():
    chunks = svc.chunk_text("a" * 1200)
    assert len(chunks) == 3
    assert all(len(c) <= 500 for c in chunks)


def test_chunk_text_merge_short():
    chunks = svc.chunk_text("x" * 490 + "\n\n" + "y" * 20)
    assert len(chunks) == 1
    assert len(chunks[0]) == 511


def test_chunk_text_no_chunk_over_800():
    chunks = svc.chunk_text("字" * 3000)
    assert all(len(c) <= 800 for c in chunks)


# ---------- 向量化 ----------


def test_embed_text_dimension():
    v = embed_text("测试文本")
    assert len(v) == 1536


def test_embed_text_deterministic():
    assert embed_text("abc") == embed_text("abc")


# ---------- 状态机 ----------


async def test_process_success(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    doc = await _make_doc(db_session, user, kb)

    doc = await svc.process_document(doc, "hello world".encode("utf-8"), "txt", db_session)
    assert doc.status == DocumentStatus.processed.value
    assert doc.extracted_content == "hello world"
    assert doc.chunk_count >= 1
    assert doc.error_message is None
    # 切片级向量化（doc 15 §4.1）：逐段写入 document_chunks，文档级单向量置空
    assert doc.embedding is None
    chunks = (
        await db_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
    ).scalars().all()
    assert len(chunks) == doc.chunk_count
    assert all(len(c.embedding) == 1536 for c in chunks)


async def test_process_failed_on_empty(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    doc = await _make_doc(db_session, user, kb)

    doc = await svc.process_document(doc, b"", "txt", db_session)
    assert doc.status == DocumentStatus.failed.value
    assert doc.error_message


# ---------- 删除级联与所有权 ----------


async def test_delete_document(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    doc = await _make_doc(db_session, user, kb)

    await svc.delete_document(doc.id, user, db_session)
    assert await db_session.get(Document, doc.id) is None


async def test_ownership_isolation(db_session):
    owner = await _make_user(db_session, "owner")
    other = await _make_user(db_session, "other")
    kb = await _make_kb(db_session)
    doc = await _make_doc(db_session, owner, kb)

    with pytest.raises(HTTPException) as e:
        await svc.get_document(doc.id, other, db_session)
    assert e.value.status_code == 404

    assert len(await svc.list_documents(other, db_session)) == 0
    assert len(await svc.list_documents(owner, db_session)) == 1


async def test_get_document_chunks(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    doc = await _make_doc(db_session, user, kb)
    doc.extracted_content = "A" * 300 + "\n\n" + "B" * 300
    await db_session.flush()

    chunks = await svc.get_document_chunks(doc.id, user, db_session)
    assert chunks == ["A" * 300, "B" * 300]
