"""LLM 服务（Qwen）：走库判断分类、查询改写、答案生成（doc 15 §4.2 + doc 40）。

未配置 `llm_base_url` / `llm_api_key` 时走确定性 mock（分类/改写/生成均可离线测试）；
配置后调用 OpenAI 兼容 `/chat/completions`（预留钩子，见 `_classify_remote` 等）。
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.embedding_service import tokenize_text

# GENERAL 主题关键词：命中则分类为 GENERAL（闲聊应答，不走库检索）
GENERAL_TOPIC_KEYWORDS = (
    "讲个笑话",
    "你会什么",
    "天气",
    "推荐",
    "电影",
    "唱歌",
    "你是谁",
    "自我介绍",
    "闲聊",
    "聊天",
)


def extract_keywords(text: str, limit: int = 6) -> list[str]:
    """提取去重关键词（中文 bigram + ASCII 单词），最多 limit 个。"""
    seen: set[str] = set()
    out: list[str] = []
    for tok in tokenize_text(text):
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
            if len(out) >= limit:
                break
    return out


class LLMClient:
    """LLM 客户端。无密钥时 mock 模式，配置后走真实 API（预留钩子）。"""

    @property
    def mock_mode(self) -> bool:
        return not settings.llm_configured

    def classify_kb(self, question: str) -> str:
        """走库判断第二层：分类 `KB` / `GENERAL`。"""
        if self.mock_mode:
            q = (question or "").strip().lower()
            if any(k in q for k in GENERAL_TOPIC_KEYWORDS):
                return "GENERAL"
            return "KB"
        return self._classify_remote(question)

    def rewrite_query(self, question: str) -> dict[str, Any]:
        """查询改写：产出 `rewritten_query` + `expanded_keywords`（≤6）。"""
        if self.mock_mode:
            return {
                "rewritten_query": (question or "").strip(),
                "expanded_keywords": extract_keywords(question, limit=6),
            }
        return self._rewrite_remote(question)

    def generate_answer(self, question: str, chunks: list[dict]) -> str:
        """基于检索片段生成回答（仅依据片段，防幻觉）。"""
        if self.mock_mode:
            if not chunks:
                return ""
            names = "、".join(
                dict.fromkeys(c.get("document_name", "文档") for c in chunks)
            )
            first = chunks[0].get("chunk_text", "")
            return f"根据《{names}》：{first}"
        return self._generate_remote(question, chunks)

    # ---------- 真实 API 钩子（未接入） ----------

    def _classify_remote(self, question: str) -> str:
        raise NotImplementedError("真实 LLM API 尚未接入")

    def _rewrite_remote(self, question: str) -> dict[str, Any]:
        raise NotImplementedError("真实 LLM API 尚未接入")

    def _generate_remote(self, question: str, chunks: list[dict]) -> str:
        raise NotImplementedError("真实 LLM API 尚未接入")


# 服务层共享的默认客户端
llm_client = LLMClient()
