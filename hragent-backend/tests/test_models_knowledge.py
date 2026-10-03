"""知识模型单元测试：KnowledgeBase + Document（embedding Vector(1536)）。"""
from app.models import Document, KnowledgeBase


async def test_knowledge_base_unique_name(db_session):
    import pytest
    from sqlalchemy.exc import IntegrityError

    db_session.add(KnowledgeBase(name="公司制度"))
    await db_session.flush()
    db_session.add(KnowledgeBase(name="公司制度"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_document_embedding_roundtrip(db_session):
    kb = KnowledgeBase(name="制度库")
    db_session.add(kb)
    await db_session.flush()

    doc = Document(
        filename="员工手册.pdf",
        knowledge_base_id=kb.id,
        embedding=[0.1] * 1536,
    )
    db_session.add(doc)
    await db_session.flush()
    await db_session.refresh(doc)

    assert doc.embedding is not None
    assert len(doc.embedding) == 1536
    assert abs(doc.embedding[0] - 0.1) < 1e-5
