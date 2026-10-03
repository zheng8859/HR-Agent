"""RAG 服务测试：余弦/向量分、0.7·0.3 合并、阈值过滤、全文检索、检索排序、来源片段、拒答。"""
import pytest

from app.models import Document, DocumentStatus, KnowledgeBase, User
from app.services import rag_service
from app.services.embedding_service import embed_text
from app.services.enhanced_document_service import chunk_text


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


async def _make_doc(db_session, user, kb, filename, content):
    doc = Document(
        filename=filename,
        original_filename=filename,
        status=DocumentStatus.processed.value,
        chunk_count=len(chunk_text(content)),
        extracted_content=content,
        embedding=embed_text(content),
        user_id=user.id,
        knowledge_base_id=kb.id,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


# ---------- 纯函数：余弦 / 向量分 / 合并 / 阈值 ----------


def test_cosine_identical():
    v = [1.0, 0.0, 0.0]
    assert rag_service.cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal():
    assert rag_service.cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_zero_vector():
    assert rag_service.cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_vector_score_identical_and_clamped():
    assert rag_service.vector_score([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert rag_service.vector_score([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    # 负相关钳制为 0
    assert rag_service.vector_score([1.0, 0.0], [-1.0, 0.0]) == 0.0


def test_combine_scores_weighting():
    # 0.7 × 向量分 + 0.3 × 文本分
    assert rag_service.combine_scores(0.5, 1.0) == pytest.approx(0.7 * 0.5 + 0.3 * 1.0)
    assert rag_service.combine_scores(1.0, 0.0) == pytest.approx(0.7)


def test_filter_below_threshold():
    scored = [
        {"id": "a", "score": 0.8},
        {"id": "b", "score": 0.19},
        {"id": "c", "score": 0.2},
    ]
    kept = rag_service.filter_below_threshold(scored, threshold=0.2)
    assert [s["id"] for s in kept] == ["a", "c"]


# ---------- 全文检索（tsvector） ----------


async def test_fulltext_english_match(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    await _make_doc(db_session, user, kb, "policy.txt", "remote work policy allows three days per week")
    scores = await rag_service._fulltext_scores("remote work policy", user.id, None, db_session)
    assert len(scores) == 1
    assert list(scores.values())[0] > 0.0


# ---------- 检索排序 ----------


async def test_retrieve_ranks_matching_doc_first(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    d1 = await _make_doc(
        db_session, user, kb, "差旅管理办法.pdf",
        "一线城市出差住宿标准为500元每间每晚，新一线城市为380元。",
    )
    d2 = await _make_doc(
        db_session, user, kb, "年假规则.pdf",
        "员工入职满一年可享五天年假，司龄每满一年增加一天。",
    )
    scored = await rag_service.retrieve("出差住宿标准", user, None, db_session)
    assert scored[0]["document"].id == d1.id
    assert scored[0]["score"] > scored[1]["score"]


# ---------- 问答编排：有依据 / 无依据 / 闲聊 ----------


async def test_ask_returns_answer_and_sources(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    await _make_doc(
        db_session, user, kb, "差旅管理办法.pdf",
        "一线城市出差住宿标准为500元每间每晚，新一线城市为380元。",
    )
    result = await rag_service.ask("出差住宿标准", user, None, db_session)
    assert result["answered"] is True
    assert result["intent"] == "KB"
    assert result["answer"]
    assert len(result["document_chunks"]) >= 1
    assert result["document_chunks"][0]["document_name"] == "差旅管理办法.pdf"
    assert result["confidence"] >= 0.2


async def test_ask_with_long_document_matches(db_session):
    """长文档 + 短问句：mock 词面覆盖应命中（防长度稀释回归，doc 40 联调发现）。"""
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    await _make_doc(
        db_session,
        user,
        kb,
        "差旅管理办法.pdf",
        "第四章 住宿及差旅标准 第4.2条：因公出差普通雇员住宿报销标准实行区域限额制。"
        "一线城市（北上广深）：普通员工住宿上限为 500 元/间/夜；"
        "新一线及各省会城市：住宿上限为 380 元/间/夜。"
        "任何超标准开支需事前递交 OA 走部门总监级特殊批准单，"
        "并在差旅终结后 5 个工作日内附审批凭证递交财务部清算。",
    )
    result = await rag_service.ask("出差住宿标准是多少", user, None, db_session)
    assert result["answered"] is True
    assert result["document_chunks"]
    assert result["document_chunks"][0]["document_name"] == "差旅管理办法.pdf"


async def test_ask_refuses_when_no_match(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    await _make_doc(
        db_session, user, kb, "年假规则.pdf",
        "员工入职满一年可享五天年假。",
    )
    result = await rag_service.ask("商业健康意外险理赔周期", user, None, db_session)
    assert result["answered"] is False
    assert result["intent"] == "KB"
    assert result["document_chunks"] == []
    assert "资料不足" in result["answer"]


async def test_ask_chitchat_general_no_retrieval(db_session):
    user = await _make_user(db_session)
    result = await rag_service.ask("你好", user, None, db_session)
    assert result["intent"] == "GENERAL"
    assert result["answered"] is True
    assert result["document_chunks"] == []
