"""走库判断（doc 15 §4.2 + doc 40）：闲聊关键词预筛 → LLM 分类 KB/GENERAL。

两层策略：闲聊短语精确命中直接应答（不走库）；否则由 LLM 分类。
"""
from __future__ import annotations

import re

from app.services.llm_service import llm_client

# 闲聊短语（归一化：去空白/标点后精确匹配）
CHITCHAT_PHRASES = {
    "你好",
    "您好",
    "你好呀",
    "早上好",
    "下午好",
    "晚上好",
    "谢谢",
    "谢谢啊",
    "感谢",
    "多谢",
    "在吗",
    "在不在",
    "嗨",
    "hi",
    "hello",
    "再见",
    "拜拜",
    "你是谁",
    "你是谁呀",
    "你是谁啊",
    "在吗?",
}

_PUNCT_RE = re.compile(r"[\s，。！？!?,.\"“”''、:：;；]+")


def is_chitchat(question: str) -> bool:
    """闲聊关键词预筛：归一化（去空白/标点）后精确命中闲聊短语。"""
    q = (question or "").strip()
    if not q:
        return True
    normalized = _PUNCT_RE.sub("", q.lower())
    return normalized in CHITCHAT_PHRASES


def should_use_kb(question: str) -> bool:
    """判断问题是否走知识库：闲聊预筛不命中，且 LLM 分类为 KB。"""
    if is_chitchat(question):
        return False
    return llm_client.classify_kb(question) == "KB"
