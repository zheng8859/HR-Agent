"""RAG 服务测试：余弦/向量分、0.7·0.3 合并、阈值过滤、全文检索、检索排序、来源片段、拒答。"""
import uuid
from types import SimpleNamespace

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


def test_embedding_similarity_maxpools_chunks(monkeypatch):
    """回归：真实 embedding 下文档向量分取切片 max-pool，长文档靠后切片可被召回。"""
    monkeypatch.setattr(rag_service.settings, "embedding_base_url", "http://x")
    monkeypatch.setattr(rag_service.settings, "embedding_api_key", "k")
    doc = SimpleNamespace(extracted_content="忽略")
    query_vec = [1.0, 0.0]
    near = SimpleNamespace(embedding=[1.0, 0.0])  # 余弦 1.0
    far = SimpleNamespace(embedding=[0.0, 1.0])  # 余弦 0.0
    assert rag_service._embedding_similarity("q", doc, query_vec, [near, far]) == pytest.approx(1.0)
    assert rag_service._embedding_similarity("q", doc, query_vec, [far]) == pytest.approx(0.0)
    assert rag_service._embedding_similarity("q", doc, query_vec, []) == 0.0


# ---------- 全文检索（jieba + IDF，替代 tsvector 'simple'） ----------


async def test_lexical_fulltext_english_match(db_session):
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    doc = await _make_doc(
        db_session, user, kb, "policy.txt",
        "remote work policy allows three days per week",
    )
    docs = await rag_service._candidate_documents(user, None, db_session)
    scores = rag_service._lexical_fulltext_scores("remote work policy", docs)
    assert scores[doc.id] > 0.0


async def test_lexical_fulltext_chinese_matches_content_word(db_session):
    """回归：中文全文分应命中内容词，且泛词（公司/有/哪些）不应把无关文档抬分。"""
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    asset = await _make_doc(
        db_session, user, kb, "资产管理制度.txt",
        "资产的分类：根据资产的使用形态，分为固定资产和虚拟资产两类。"
        "固定资产包括显示器、主机、笔记本、手机、图书、桌椅、直播设备等。",
    )
    leave = await _make_doc(
        db_session, user, kb, "年假规则.txt",
        "员工入职满一年可享五天年假，司龄每满一年增加一天。",
    )
    docs = await rag_service._candidate_documents(user, None, db_session)
    scores = rag_service._lexical_fulltext_scores("资产分类有哪些", docs)
    assert scores[asset.id] > scores[leave.id] >= 0.0
    # 无内容词命中的问句（健身房/补贴）即便含泛词「公司/有/吗」也不得给高分
    scores2 = rag_service._lexical_fulltext_scores("公司有健身房补贴吗", docs)
    assert max(scores2.values()) < 0.2


async def test_ask_chinese_section_answer_not_refused(db_session):
    """回归：长文档靠后小节（资产分类）的答案不能被 0.2 阈值误杀成「资料不足」。"""
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    await _make_doc(
        db_session, user, kb, "人事管理流程.txt",
        "一、聘用管理：基础岗位由部门主管面试确定，管理岗位由总经理面试确定。\n\n"
        "二、资产的分类：根据资产的使用形态，分为固定资产和虚拟资产两类。"
        "固定资产包括显示器、主机、笔记本、手机、图书、桌椅、直播设备等。",
    )
    await _make_doc(
        db_session, user, kb, "年假规则.txt",
        "员工入职满一年可享五天年假。",
    )
    result = await rag_service.ask("资产分类有哪些", user, None, db_session)
    assert result["answered"] is True
    assert result["intent"] == "KB"
    assert result["document_chunks"]
    assert "固定资产" in result["answer"] and "虚拟资产" in result["answer"]


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


# ---------- 来源片段全局排序（回归：答案段被邻近话题段挤掉） ----------


def _fake_doc(filename: str, content: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        original_filename=filename,
        filename=filename,
        extracted_content=content,
    )


def test_chunk_relevance_prefers_frequent_answer_over_one_off_mention():
    """回归：旧实现用「是否出现」的 lexical_overlap 选段，顺带提及多个查询词但未给出答案的
    邻近段可能词面得分更高、挤掉真正答案段；chunk_relevance 按词项频次加权，答案段应更高分。"""
    question = "离职需要提前多久申请"
    keywords = ["离职", "申请", "提前"]
    # 顺带提及段：覆盖「离职/需要/多久/申请/提前」五个查询词，但每个只出现一次
    distractor = "员工离职需要多久申请，需提前向人事部门报备。"
    # 答案段：只覆盖「离职/申请/提前」三个查询词，但反复命中
    answer = "试用期内离职需提前7天申请，转正后离职需提前1个月申请。"

    # 旧 lexical_overlap 只看「是否出现」：顺带段覆盖更多查询词，得分反而更高
    assert rag_service.lexical_overlap(question, distractor) > rag_service.lexical_overlap(
        question, answer
    ), "前提：该样本在旧打分下会选错段，否则无法充当回归用例"
    # 新 chunk_relevance 按词项频次加权：答案段反复命中主题，应更高
    assert rag_service.chunk_relevance(question, keywords, answer) > rag_service.chunk_relevance(
        question, keywords, distractor
    )


def test_build_source_chunks_global_ranking_selects_answer_chunk():
    """回归：旧实现每文档只取「词面最相关 1 段」，长文档中真正的答案段会被邻近话题段
    （如「转正」段顺带提「离职」）挤掉，导致 LLM 把「资料有说明」答成「资料无说明」。

    新实现跨文档全局按片段相关性取 Top-K，答案段应排在第一。
    """
    # 三段：晋升（无关）、试用与转正（顺带提「申请/提前」，但无离职时限）、离职（答案段）。
    # 每段足够长（≈300 字），使 chunk_text 分成多段而非合并成一段。
    promotion = (
        "四、晋升管理：公司实行德能与业绩并重的晋升原则，能升能降，职位能者居之。"
        "晋升流程由用人部门提名，人事行政部组织综合能力与绩效评估，评估合格后报总经理审批。"
        "审批通过后办理晋升手续并同步调整薪资待遇，晋升结果以正式任免文件为准并向全公司公示。"
        "各部门晋升名额按年度编制与人员结构统筹确定，晋升人员需满足任职年限与绩效等级要求。"
        "晋升人员需参加干部考察与民主评议，评议结果作为任免的重要依据并存入个人人事档案。"
    )
    probation = (
        "五、试用与转正：试用期一般为1-3个月，试用期合格与否由用人部门提前7天告知人事行政部。"
        "员工填写转正申请后走审批流程，由人事行政部审批，审批通过后办理转正手续并归档人事档案。"
        "转正后按公司薪酬体系调整相应待遇标准，转正申请需附工作考核结果与部门主管评价意见。"
        "试用期考核不合格的，公司可依法解除劳动合同或延长试用期至规定上限。"
        "试用期内员工应完成入职培训并通过岗位技能考核，考核成绩作为转正评估的重要参考。"
    )
    resignation = (
        "六、离职管理：试用期内离职需提前7天向公司提交申请，转正后离职需提前1个月向公司提交申请。"
        "离职需按规定办理工作交接与离职手续，离职申请需同步人事部门审批后方可办理。"
        "员工离职时应归还公司财物、注销相关权限，并在离职当日办结工资结算与社保转移事宜。"
        "离职未按规定时间提前申请的，公司有权按规定扣发相应工资；离职手续办结后方可开具离职证明。"
    )
    doc = _fake_doc("人事管理流程.txt", promotion + "\n\n" + probation + "\n\n" + resignation)
    ranked = [{"document": doc, "score": 0.3}]

    chunks = rag_service.build_source_chunks(
        "离职需要提前多久申请", ranked, ["离职", "申请", "提前"], limit=3
    )

    assert chunks, "应返回来源片段"
    top = chunks[0]["chunk_text"]
    assert ("7天" in top) or ("1个月" in top) or ("一个月" in top), (
        f"答案段应排第一，实际首段：{top!r}"
    )


async def test_ask_multi_section_doc_answers_from_relevant_chunk(db_session):
    """回归：多段文档中答案在特定段落，问答应命中该段而非顺带提及的邻近段。"""
    user = await _make_user(db_session)
    kb = await _make_kb(db_session)
    content = (
        "四、晋升管理：公司实行德能与业绩并重的晋升原则，能升能降，职位能者居之。"
        "晋升流程由用人部门提名，人事行政部组织评估，报总经理审批后办理晋升手续并调整薪资。\n\n"
        "五、试用与转正：试用期一般为1-3个月，合格与否由用人部门提前7天告知人事行政部，"
        "员工填写转正申请走审批流程。\n\n"
        "六、离职管理：试用期内离职需提前7天向公司提交申请，转正后离职需提前1个月向公司提交申请，"
        "离职需办理工作交接与离职手续。"
    )
    await _make_doc(db_session, user, kb, "人事管理流程.txt", content)
    result = await rag_service.ask("离职需要提前多久申请", user, None, db_session)
    assert result["answered"] is True
    assert result["intent"] == "KB"
    assert ("7天" in result["answer"]) or ("1个月" in result["answer"]) or (
        "一个月" in result["answer"]
    ), f"应命中离职时限答案，实际：{result['answer']!r}"
