"""LLM 服务测试（mock 模式）：走库分类、查询改写（≤6 关键词）、答案生成带来源。"""
from app.services.llm_service import extract_keywords, llm_client


def test_classify_kb_policy_question():
    assert llm_client.classify_kb("年假休假规则怎么算") == "KB"
    assert llm_client.classify_kb("出差住宿报销上限是多少") == "KB"


def test_classify_kb_general_smalltalk():
    assert llm_client.classify_kb("讲个笑话") == "GENERAL"
    assert llm_client.classify_kb("今天天气怎么样") == "GENERAL"


def test_rewrite_query_keywords_at_most_six():
    rw = llm_client.rewrite_query("出差住宿标准与报销上限")
    assert "rewritten_query" in rw
    assert rw["rewritten_query"] == "出差住宿标准与报销上限"
    assert 1 <= len(rw["expanded_keywords"]) <= 6


def test_extract_keywords_unique_and_capped():
    kw = extract_keywords("出差 出差 住宿 标准", limit=2)
    assert len(kw) <= 2
    assert kw == list(dict.fromkeys(kw))  # 去重


def test_generate_answer_cites_source():
    chunks = [{"document_name": "差旅管理办法.pdf", "chunk_text": "一线城市住宿上限 500 元"}]
    answer = llm_client.generate_answer("住宿上限", chunks)
    assert "差旅管理办法" in answer
    assert "500" in answer
