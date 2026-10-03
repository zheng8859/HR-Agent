"""Embedding 向量化服务（doc 39 §向量化）。

未配置 `embedding_base_url` / `embedding_api_key` 时走确定性 mock：
对文本 hash 派生固定 1536 维单位向量，同一文本恒定、维度一致，供离线测试与联调。
配置后走真实 Embedding API（预留钩子，见 `_embed_remote`）。
"""
from __future__ import annotations

import hashlib
import math
import random

from app.core.config import settings


def _mock_embed(text: str) -> list[float]:
    """对文本 hash 派生确定性 1536 维单位向量。"""
    seed = int.from_bytes(
        hashlib.sha256(text.encode("utf-8")).digest()[:8], "big"
    )
    rng = random.Random(seed)
    vec = [rng.uniform(-1.0, 1.0) for _ in range(settings.embedding_dimension)]
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def _embed_remote(text: str) -> list[float]:
    """调用真实 Embedding API（预留钩子，未接入）。"""
    raise NotImplementedError("真实 Embedding API 尚未接入")


def embed_text(text: str) -> list[float]:
    """返回文本的 1536 维向量；未配置时走确定性 mock。"""
    if settings.embedding_configured:
        return _embed_remote(text)
    return _mock_embed(text)
