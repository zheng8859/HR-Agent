"""知识库服务单元测试：CRUD、名称唯一、含文档拒绝删除。"""
import pytest
from fastapi import HTTPException

from app.models import Document, DocumentStatus, KnowledgeBase, User
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.services import knowledge_base_service as svc


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
    kb = KnowledgeBase(name=name, description="测试", document_count=0)
    db_session.add(kb)
    await db_session.flush()
    return kb


async def test_create_and_get(db_session):
    kb = await svc.create_kb(
        KnowledgeBaseCreate(name="员工手册", description="入职指南"), db_session
    )
    assert kb.name == "员工手册"
    assert (await db_session.get(KnowledgeBase, kb.id)) is not None


async def test_name_unique_conflict(db_session):
    await _make_kb(db_session, "员工手册")
    with pytest.raises(HTTPException) as e:
        await svc.create_kb(KnowledgeBaseCreate(name="员工手册"), db_session)
    assert e.value.status_code == 409


async def test_update_and_list(db_session):
    kb = await _make_kb(db_session, "旧名")
    updated = await svc.update_kb(
        kb.id, KnowledgeBaseUpdate(name="新名", description="新描述"), db_session
    )
    assert updated.name == "新名"
    assert updated.description == "新描述"
    names = [k.name for k in await svc.list_kbs(db_session)]
    assert "新名" in names


async def test_update_name_conflict_with_other(db_session):
    kb = await _make_kb(db_session, "A")
    await _make_kb(db_session, "B")
    with pytest.raises(HTTPException) as e:
        await svc.update_kb(kb.id, KnowledgeBaseUpdate(name="B"), db_session)
    assert e.value.status_code == 409


async def test_update_self_same_name_ok(db_session):
    kb = await _make_kb(db_session, "A")
    updated = await svc.update_kb(kb.id, KnowledgeBaseUpdate(name="A"), db_session)
    assert updated.name == "A"


async def test_get_missing_404(db_session):
    import uuid

    with pytest.raises(HTTPException) as e:
        await svc.get_kb(uuid.uuid4(), db_session)
    assert e.value.status_code == 404


async def test_delete_with_documents_409(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    doc = Document(
        filename="a.txt",
        original_filename="a.txt",
        status=DocumentStatus.processed.value,
        chunk_count=1,
        user_id=user.id,
        knowledge_base_id=kb.id,
    )
    db_session.add(doc)
    await db_session.flush()

    with pytest.raises(HTTPException) as e:
        await svc.delete_kb(kb.id, db_session)
    assert e.value.status_code == 409


async def test_delete_empty_kb(db_session):
    kb = await _make_kb(db_session)
    await svc.delete_kb(kb.id, db_session)
    assert await db_session.get(KnowledgeBase, kb.id) is None
