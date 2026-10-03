"""RAG 问答管线（doc 15 §4.2 + doc 17 §五 + doc 40）。

检索粒度为文档级（`Document.embedding` 单向量，不新增切片表）；来源片段由命中文档的
`extracted_content` 现场 `chunk_text` 切片、选与问题词面最相关的一段派生。

流程：走库判断 → 查询改写 → 多路径检索（向量余弦 + tsvector 全文）→ 0.7/0.3 加权合并
→ 阈值过滤 → Rerank（失败降级）→ LLM 生成 + 来源；无依据拒答。
"""
from __future__ import annotations

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Document, DocumentStatus, User
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


# ---------- 检索 ----------


async def _candidate_documents(
    user: User, knowledge_base_id: uuid.UUID | None, db: AsyncSession
) -> list[Document]:
    """候选文档：当前用户已处理且有向量的文档（可按知识库过滤）。"""
    stmt = select(Document).where(
        Document.user_id == user.id,
        Document.status == DocumentStatus.processed.value,
        Document.embedding.isnot(None),
    )
    if knowledge_base_id is not None:
        stmt = stmt.where(Document.knowledge_base_id == knowledge_base_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _fulltext_scores(
    question: str,
    user_id: uuid.UUID,
    knowledge_base_id: uuid.UUID | None,
    db: AsyncSession,
) -> dict[uuid.UUID, float]:
    """PostgreSQL tsvector 全文检索：命中文档的 `ts_rank` 归一化到 [0,1]。"""
    tsvector = func.to_tsvector("simple", Document.extracted_content)
    tsquery = func.plainto_tsquery("simple", question)
    stmt = select(Document.id, func.ts_rank(tsvector, tsquery)).where(
        Document.user_id == user_id,
        Document.status == DocumentStatus.processed.value,
        tsvector.op("@@")(tsquery),
    )
    if knowledge_base_id is not None:
        stmt = stmt.where(Document.knowledge_base_id == knowledge_base_id)
    rows = (await db.execute(stmt)).all()
    if not rows:
        return {}
    max_rank = max((r[1] for r in rows), default=0.0) or 1.0
    return {r[0]: float(r[1]) / float(max_rank) for r in rows}


def _embedding_similarity(
    question: str, doc: Document, query_vec: list[float]
) -> float:
    """向量分：真实 embedding 用余弦相似度；mock（未配置 embedding）退回词面覆盖率。

    词面 bag-of-words 的 mock 向量在「短问句 vs 长文档」下余弦会被文档长度稀释（分母
    sqrt(|q|·|d|）），导致明显相关的长文档余弦过低、被 0.2 阈值误杀。改用查询词项在
    文档中的覆盖占比，让离线态检索也能命中长文档（真实 embedding 不受此影响）。
    """
    if settings.embedding_configured:
        return vector_score(query_vec, list(doc.embedding))
    return lexical_overlap(question, doc.extracted_content or "")


async def retrieve(
    question: str,
    user: User,
    knowledge_base_id: uuid.UUID | None,
    db: AsyncSession,
) -> list[dict]:
    """多路径检索：向量 + 全文，0.7/0.3 加权合并，返回按合并分降序的列表。"""
    query_vec = embed_text(question)
    docs = await _candidate_documents(user, knowledge_base_id, db)
    text_scores = await _fulltext_scores(question, user.id, knowledge_base_id, db)
    scored: list[dict] = []
    for doc in docs:
        vs = _embedding_similarity(question, doc, query_vec)
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
    question: str, ranked: list[dict], limit: int | None = None
) -> list[dict]:
    """对命中文档各取词面最相关的一段作为来源片段（带文档名与相似度）。"""
    limit = settings.rag_source_chunks if limit is None else limit
    chunks: list[dict] = []
    for r in ranked:
        doc = r["document"]
        doc_chunks = chunk_text(doc.extracted_content)
        if not doc_chunks:
            continue
        best = max(doc_chunks, key=lambda c: lexical_overlap(question, c))
        chunks.append(
            {
                "document_id": doc.id,
                "document_name": doc.original_filename or doc.filename,
                "chunk_text": best,
                "similarity": round(r["score"], 4),
            }
        )
        if len(chunks) >= limit:
            break
    return chunks


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

    chunks = build_source_chunks(rewritten, reranked, settings.rag_source_chunks)
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
