"""知识模型单元测试：KnowledgeBase + Document + DocumentChunk（embedding Vector(1536)）。"""
from sqlalchemy import select

from app.models import Document, DocumentChunk, KnowledgeBase


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


async def test_document_chunk_roundtrip_and_cascade(db_session):
    """切片实体：document_id 外键 + chunk_index 顺序 + 向量 round-trip + 级联删除。"""
    kb = KnowledgeBase(name="制度库")
    db_session.add(kb)
    await db_session.flush()
    doc = Document(filename="员工手册.pdf", knowledge_base_id=kb.id)
    db_session.add(doc)
    await db_session.flush()

    c1 = DocumentChunk(document_id=doc.id, chunk_index=0, chunk_text="第一节", embedding=[0.1] * 1536)
    c2 = DocumentChunk(document_id=doc.id, chunk_index=1, chunk_text="第二节", embedding=[0.2] * 1536)
    db_session.add_all([c1, c2])
    await db_session.flush()

    chunks = (
        await db_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
    ).scalars().all()
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert len(chunks[0].embedding) == 1536
    assert abs(chunks[0].embedding[0] - 0.1) < 1e-5

    # 级联：删除文档应连带删除其切片
    await db_session.delete(doc)
    await db_session.flush()
    remaining = (
        await db_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
    ).scalars().all()
    assert remaining == []
