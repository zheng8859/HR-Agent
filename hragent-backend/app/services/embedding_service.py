"""Embedding 向量化服务（doc 39 §向量化 + doc 40 §检索）。

未配置 `embedding_base_url` / `embedding_api_key` 时走确定性 mock：
对文本词面 token（中文 bigram + ASCII 单词）做 feature hashing 到 1536 维并 L2 归一化，
词面重叠越高的文本余弦相似度越高，供离线态 RAG 检索排序；同一文本恒定、维度一致。
配置后走真实 Embedding API（预留钩子，见 `_embed_remote`）。
"""
from __future__ import annotations

import hashlib
import math
import random
import re

import httpx

from app.core.config import settings

# 真实 Embedding 输入上限（text-embedding-v2 约 2048 token，中文按 ~1 token/字保守截断，避免超长文档报错）
_MAX_EMBED_CHARS = 1800


def tokenize_text(text: str) -> list[str]:
    """词面 token：中文字符 bigram + ASCII 单词（小写）。

    供 mock 向量、查询改写关键词与检索文本分复用。
    """
    text = (text or "").lower()
    tokens: list[str] = re.findall(r"[a-z0-9]+", text)
    for run in re.findall(r"[一-鿿]+", text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


def _mock_embed(text: str) -> list[float]:
    """词面代理向量：feature hashing 到 1536 维 + L2 归一化。"""
    tokens = tokenize_text(text)
    dim = settings.embedding_dimension
    vec = [0.0] * dim
    for tok in tokens:
        idx = int.from_bytes(
            hashlib.sha256(tok.encode("utf-8")).digest()[:4], "big"
        ) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        # 无有效 token 时回退为基于全文 hash 的确定性单位向量（保维度、确定性）
        return _random_unit_vec(text)
    return [x / norm for x in vec]


def _random_unit_vec(text: str) -> list[float]:
    """对全文 hash 派生确定性 1536 维单位向量（空 token 兜底）。"""
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    vec = [rng.uniform(-1.0, 1.0) for _ in range(settings.embedding_dimension)]
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def _embed_remote(text: str) -> list[float]:
    """调用真实 Embedding API（OpenAI 兼容 `/embeddings`），返回 `embedding_dimension` 维向量。"""
    payload = (text or "").strip()[:_MAX_EMBED_CHARS]
    if not payload:
        # 空文本无真实语义，返回零向量（模为 0，检索时余弦为 0，视为不相关）
        return [0.0] * settings.embedding_dimension
    resp = httpx.post(
        f"{settings.embedding_base_url}/embeddings",
        headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
        json={"model": settings.embedding_model, "input": payload},
        timeout=30.0,
    )
    resp.raise_for_status()
    vec = resp.json()["data"][0]["embedding"]
    return [float(x) for x in vec]


def embed_text(text: str) -> list[float]:
    """返回文本的 1536 维向量；未配置时走确定性 mock。"""
    if settings.embedding_configured:
        return _embed_remote(text)
    return _mock_embed(text)
