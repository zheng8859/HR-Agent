"""Rerank 重排服务（doc 15 §4.2 + doc 40）：gte-rerank-v2 重排 + 失败降级。

未配置 `rerank_base_url` / `rerank_api_key` 时走 mock（保持原始召回排序，仅截断 top_k）；
配置后调用真实 Rerank API（预留钩子，见 `_rerank_remote`）。任一异常必须降级，不中断。
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings


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
    """调用真实 Rerank API（预留钩子，未接入）。"""
    raise NotImplementedError("真实 Rerank API 尚未接入")
