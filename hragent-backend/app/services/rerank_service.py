"""Rerank 重排服务（doc 15 §4.2 + doc 40）：gte-rerank-v2 重排 + 失败降级。

未配置 `rerank_base_url` / `rerank_api_key` 时走 mock（保持原始召回排序，仅截断 top_k）；
配置后调用真实 Rerank API（预留钩子，见 `_rerank_remote`）。任一异常必须降级，不中断。
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings

# Rerank 单篇文档输入上限（gte-rerank-v2 约 2048 token，中文按 ~1 token/字保守截断）
_MAX_RERANK_CHARS = 1800


def _item_text(item: dict[str, Any]) -> str:
    """从检索候选项中取出用于重排的文本（优先文档正文，兼容通用 `text`/`chunk_text` 字段）。"""
    doc = item.get("document")
    if doc is not None:
        return (doc.extracted_content or doc.original_filename or "")[:_MAX_RERANK_CHARS]
    return str(item.get("text") or item.get("chunk_text") or "")[:_MAX_RERANK_CHARS]


def rerank(query: str, items: list[dict], top_k: int | None = None) -> list[dict]:
    """按 Rerank 相关性重排 items，截断到 top_k。

    `items` 为已按原始召回分降序的列表，每项至少含 `score`（与 `text`）。
    mock 态保持原序；配置后走真实 Rerank API。
    """
    if settings.rerank_configured:
        return _rerank_remote(query, items, top_k)
    return items[:top_k] if top_k is not None else items


def rerank_or_fallback(
    query: str, items: list[dict], top_k: int | None = None
) -> list[dict]:
    """重排；Rerank 任一异常回退为原始召回排序（不中断）。"""
    try:
        return rerank(query, items, top_k)
    except Exception:
        return items[:top_k] if top_k is not None else items


def _rerank_remote(query: str, items: list[dict], top_k: int | None) -> list[dict]:
    """调用真实 Rerank API（dashscope text-rerank），按相关性降序重排并截断到 top_k。"""
    if not items:
        return []
    documents = [_item_text(it) for it in items]
    n = len(documents)
    resp = httpx.post(
        settings.rerank_base_url,
        headers={"Authorization": f"Bearer {settings.rerank_api_key}"},
        json={
            "model": settings.rerank_model,
            "input": {"query": query, "documents": documents},
            "parameters": {"top_n": n, "return_documents": False},
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    results = resp.json()["output"]["results"]
    reordered = [items[int(r["index"])] for r in results if 0 <= int(r["index"]) < n]
    return reordered[:top_k] if top_k is not None else reordered
