"""RAG 问答管线（doc 15 §4.2 + doc 17 §五 + doc 40）。

检索粒度为切片级（doc 15 §4.1：`document_chunks.embedding`，逐段向量化后按文档
max-pool）；来源片段由命中文档的 `extracted_content` 现场 `chunk_text` 切片、选与
问题词面最相关的一段派生。

流程：走库判断 → 查询改写 → 多路径检索（向量余弦 + 分词全文）→ 0.7/0.3 加权合并
→ 阈值过滤 → Rerank（失败降级）→ LLM 生成 + 来源；无依据拒答。
"""
from __future__ import annotations

import math
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:  # 中文分词（doc 40 全文检索）；缺失时回退到 bigram 词面切词，保证不崩溃
    import jieba

    _HAS_JIEBA = True
except ImportError:  # pragma: no cover
    jieba = None
    _HAS_JIEBA = False

from app.core.config import settings
from app.models import Document, DocumentChunk, DocumentStatus, User
from app.services.embedding_service import embed_text, tokenize_text
from app.services.enhanced_document_service import chunk_text
from app.services.kb_selection_service import should_use_kb
from app.services.llm_service import llm_client
from app.services.rerank_service import rerank_or_fallback


# ---------- 向量相似度与打分 ----------


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """两向量余弦相似度；任一向量的模为 0 返回 0。"""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def vector_score(a: list[float], b: list[float]) -> float:
    """向量分 ∈ [0,1]：余弦相似度，负相关钳制为 0。"""
    return max(0.0, cosine_similarity(a, b))


def combine_scores(
    vector_score_: float,
    text_score: float,
    vector_weight: float | None = None,
    text_weight: float | None = None,
) -> float:
    """加权合并：0.7 × 向量分 + 0.3 × 文本分。"""
    vw = settings.rag_vector_weight if vector_weight is None else vector_weight
    tw = settings.rag_text_weight if text_weight is None else text_weight
    return vw * vector_score_ + tw * text_score


def filter_below_threshold(
    scored: list[dict], threshold: float | None = None
) -> list[dict]:
    """过滤合并分低于阈值的候选（不改变顺序）。"""
    t = settings.rag_min_similarity_score if threshold is None else threshold
    return [s for s in scored if s["score"] >= t]


def lexical_overlap(query: str, text: str) -> float:
    """查询词项在文本中的覆盖占比 ∈ [0,1]（来源片段定位用）。"""
    q_tokens = set(tokenize_text(query))
    if not q_tokens:
        return 0.0
    content = (text or "").lower()
    return sum(1 for t in q_tokens if t in content) / len(q_tokens)


def _term_coverage(terms: list[str], content: str) -> float:
    """词项在文本中的频次加权覆盖 ∈ [0,1]（单次计数上限 3，避免长词重复主导）。"""
    if not terms:
        return 0.0
    total = 0.0
    for t in terms:
        total += min(content.count(t), 3)
    return total / (len(terms) * 3)


def chunk_relevance(question: str, keywords: list[str], chunk: str) -> float:
    """片段与问题的相关性 ∈ [0,1]：原始问题词项 + 扩展关键词的频次加权覆盖。

    原始问题词项权重更高（防止 LLM 改写/扩词偏离原意），关键词用于补充同义/上位词命中。
    按出现频次（而非仅是否出现）加权，使真正反复命中主题的段落排在前、被顺带提及的
    邻近段落（如「转正」段顺带提「离职」）排在后。
    """
    content = (chunk or "").lower()
    if not content:
        return 0.0
    q_terms = tokenize_text(question)
    kw_terms = [k.lower() for k in (keywords or []) if k and k.strip()]
    return 0.6 * _term_coverage(q_terms, content) + 0.4 * _term_coverage(kw_terms, content)


# ---------- 检索 ----------


async def _candidate_documents(
    user: User, knowledge_base_id: uuid.UUID | None, db: AsyncSession
) -> list[Document]:
    """候选文档：当前用户已处理的文档（可按知识库过滤）；切片向量由 `_load_chunks` 单独取回。"""
    stmt = select(Document).where(
        Document.user_id == user.id,
        Document.status == DocumentStatus.processed.value,
    )
    if knowledge_base_id is not None:
        stmt = stmt.where(Document.knowledge_base_id == knowledge_base_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _load_chunks(
    doc_ids: list[uuid.UUID], db: AsyncSession
) -> dict[uuid.UUID, list[DocumentChunk]]:
    """一次查询取回候选文档的全部切片，按 document_id 分组（chunk_index 保序）。"""
    if not doc_ids:
        return {}
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id.in_(doc_ids))
        .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
    )
    result = await db.execute(stmt)
    grouped: dict[uuid.UUID, list[DocumentChunk]] = {}
    for c in result.scalars().all():
        grouped.setdefault(c.document_id, []).append(c)
    return grouped


def _segment(text: str) -> list[str]:
    """中文友好的分词：jieba 精确模式（中文词 + 小写 ASCII 词/数字）；缺失时回退 bigram。"""
    text = (text or "").lower()
    if _HAS_JIEBA:
        toks = [
            tok
            for tok in jieba.lcut(text)
            if tok.strip() and re.search(r"[a-z0-9一-鿿]", tok)
        ]
        if toks:
            return toks
    return tokenize_text(text)


# HR 问句里的功能词 / 泛指词：不携带主题信息，全文打分前从查询词项中剔除。否则
# 「公司/是否/提供/有/哪些」等泛词在长制度文档里高频命中，会把无关文档抬过 0.2 阈值
# （小语料下 IDF 无法区分「是否/提供」这类 df=1 的泛词与「资产/分类」这类主题词）。
_QUERY_STOPWORDS = {
    # 疑问词 / 代词
    "哪些", "什么", "如何", "怎么", "怎样", "吗", "呢", "哪", "是否", "有没有",
    "多少", "为什么", "为何", "谁", "几", "几个", "哪种", "哪类", "哪里",
    # 助词 / 介词 / 连词 / 系词
    "的", "了", "是", "有", "和", "与", "或", "及", "等", "在", "对", "从",
    "关于", "对于", "根据", "按照", "相关", "进行", "情况", "内容", "方面", "主要",
    # 泛指主语
    "公司", "员工", "我们", "你们", "他们", "我", "你", "他", "她", "它",
    # 高频泛动词 / 询问框架词
    "提供", "需要", "可以", "应该", "应当", "能够", "必须", "会", "要", "请",
    "申请", "规定", "流程", "方法", "要求", "时间", "规则", "关系", "条件", "范围",
}


def _lexical_fulltext_scores(
    question: str, docs: list[Document]
) -> dict[uuid.UUID, float]:
    """中文友好的全文分：分词 + IDF 加权词面覆盖（替代 `to_tsvector('simple')`）。

    PostgreSQL `to_tsvector('simple', …)` 对无空格中文把整段当单 token，`plainto_tsquery`
    几乎不命中 → 中文文档全文分恒为 0，0.3 文本权重形同虚设，长文档里靠后的小节（如
    「资产分类」）既超出 embedding 输入上限、又没有全文命中，被 0.2 阈值误杀成「资料不足」。

    改用 `_segment`（jieba 中文词 + ASCII 词）切词，按 IDF 对泛词（公司/有/哪些/提供…）降权，
    词项命中频次封顶 3，返回绝对值 ∈[0,1]（不按最大值归一化，弱匹配保持低分），
    避免 naive lexical_overlap 用「泛词在长文档高频命中」把无关文档抬过阈值的回退。
    """
    q_terms = [t for t in _segment(question) if t not in _QUERY_STOPWORDS]
    if not q_terms or not docs:
        return {}
    doc_tf: list[dict[str, int]] = []
    df: dict[str, int] = {}
    for d in docs:
        tf: dict[str, int] = {}
        for t in _segment(d.extracted_content or ""):
            tf[t] = tf.get(t, 0) + 1
        doc_tf.append(tf)
        for t in tf:
            df[t] = df.get(t, 0) + 1
    n = len(docs)
    # BM25 风格 IDF（平滑 +1，下限 0）→ 归一化权重，最稀有词项权重 1.0
    idf = {
        t: math.log((n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5) + 1.0)
        for t in q_terms
    }
    max_idf = max(idf.values()) or 1.0
    w = {t: idf[t] / max_idf for t in q_terms}
    total_w = sum(w.values())
    if total_w <= 0:
        return {}
    cap = 3.0
    scores: dict[uuid.UUID, float] = {}
    for d, tf in zip(docs, doc_tf):
        matched = sum(w[t] * min(tf.get(t, 0), cap) / cap for t in q_terms)
        scores[d.id] = matched / total_w
    return scores


def _embedding_similarity(
    question: str,
    doc: Document,
    query_vec: list[float],
    chunks: list[DocumentChunk] | None = None,
) -> float:
    """向量分：真实 embedding 取切片向量 max-pool 余弦；mock（未配置 embedding）退回词面覆盖率。

    切片级 embedding（doc 15 §4.1）：每个切片（≤500 字）各自向量化，长文档不再被
    `_MAX_EMBED_CHARS` 截断；检索取与问题最相似的切片作为文档向量分，靠后小节（如
    资产分类）同样可被语义召回。

    词面 bag-of-words 的 mock 向量在「短问句 vs 长文档」下余弦会被文档长度稀释（分母
    sqrt(|q|·|d|）），导致明显相关的长文档余弦过低、被 0.2 阈值误杀。mock 态改用查询
    词项在文档中的覆盖占比，让离线态检索也能命中长文档（真实 embedding 不受此影响）。
    """
    if settings.embedding_configured:
        if not chunks:
            return 0.0
        return max(
            (vector_score(query_vec, list(c.embedding)) for c in chunks), default=0.0
        )
    return lexical_overlap(question, doc.extracted_content or "")


async def retrieve(
    question: str,
    user: User,
    knowledge_base_id: uuid.UUID | None,
    db: AsyncSession,
) -> list[dict]:
    """多路径检索：向量（切片 max-pool）+ 分词全文，0.7/0.3 加权合并，返回按合并分降序的列表。"""
    query_vec = embed_text(question)
    docs = await _candidate_documents(user, knowledge_base_id, db)
    chunks_by_doc = await _load_chunks([d.id for d in docs], db)
    text_scores = _lexical_fulltext_scores(question, docs)
    scored: list[dict] = []
    for doc in docs:
        vs = _embedding_similarity(question, doc, query_vec, chunks_by_doc.get(doc.id))
        ts = text_scores.get(doc.id, 0.0)
        scored.append(
            {
                "document": doc,
                "vector_score": vs,
                "text_score": ts,
                "score": combine_scores(vs, ts),
            }
        )
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored


# ---------- 来源片段 ----------


def build_source_chunks(
    question: str,
    ranked: list[dict],
    keywords: list[str] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """对命中文档按片段相关性取 Top-K 片段（跨文档全局排序，非每文档取一段）。

    旧实现每文档只取「词面最相关的 1 段」，长文档中真正的答案段常被邻近话题段
    （如「转正」段顺带提「离职」）挤掉，导致 LLM 拿到错误上下文、按「仅依据参考资料」
    的约束答成「资料无此说明」。改为：对全部命中文档的所有切片统一按相关性打分、
    取前 limit 段，既作来源依据也作生成上下文。
    """
    limit = settings.rag_source_chunks if limit is None else limit
    keywords = keywords or []
    candidates: list[dict] = []
    for r in ranked:
        doc = r["document"]
        for c in chunk_text(doc.extracted_content):
            candidates.append(
                {
                    "document_id": doc.id,
                    "document_name": doc.original_filename or doc.filename,
                    "chunk_text": c,
                    "similarity": round(chunk_relevance(question, keywords, c), 4),
                    "_doc_score": r["score"],
                }
            )
    candidates.sort(key=lambda c: (c["similarity"], c["_doc_score"]), reverse=True)
    return [
        {
            "document_id": c["document_id"],
            "document_name": c["document_name"],
            "chunk_text": c["chunk_text"],
            "similarity": c["similarity"],
        }
        for c in candidates[:limit]
    ]


# ---------- 问答编排 ----------


def _chitchat_answer() -> dict:
    return {
        "answer": "你好，我是 HR 智能助手，可以帮你查询企业制度、政策与流程相关问题。",
        "answered": True,
        "confidence": 1.0,
        "intent": "GENERAL",
        "rewritten_query": None,
        "expanded_keywords": [],
        "document_chunks": [],
    }


def _refusal_answer(rewritten_query: str | None, expanded_keywords: list[str]) -> dict:
    return {
        "answer": (
            "资料不足：未在当前知识库中检索到与问题相关的依据，为避免无依据推断，"
            "暂不回答。建议补充相关制度文档或联系 HR 服务台。"
        ),
        "answered": False,
        "confidence": 0.0,
        "intent": "KB",
        "rewritten_query": rewritten_query,
        "expanded_keywords": expanded_keywords,
        "document_chunks": [],
    }


async def ask(
    question: str,
    user: User,
    knowledge_base_id: uuid.UUID | None,
    db: AsyncSession,
) -> dict:
    """RAG 问答主流程：走库判断 → 改写 → 检索 → 过滤 → 重排 → 生成。"""
    if not should_use_kb(question):
        return _chitchat_answer()

    rw = llm_client.rewrite_query(question)
    rewritten = rw["rewritten_query"] or question
    scored = await retrieve(rewritten, user, knowledge_base_id, db)
    above = filter_below_threshold(scored)

    if not above:
        return _refusal_answer(rw["rewritten_query"], rw["expanded_keywords"])

    top = above[: settings.rag_top_k]
    reranked = rerank_or_fallback(rewritten, top, settings.rerank_top_k)

    chunks = build_source_chunks(
        question, reranked, rw["expanded_keywords"], settings.rag_source_chunks
    )
    answer = llm_client.generate_answer(question, chunks)
    confidence = max((s["score"] for s in reranked), default=0.0)

    return {
        "answer": answer,
        "answered": True,
        "confidence": round(confidence, 4),
        "intent": "KB",
        "rewritten_query": rw["rewritten_query"],
        "expanded_keywords": rw["expanded_keywords"],
        "document_chunks": chunks,
    }
