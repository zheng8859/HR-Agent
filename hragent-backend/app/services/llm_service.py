"""LLM 服务（Qwen）：走库判断分类、查询改写、答案生成（doc 15 §4.2 + doc 40）。

未配置 `llm_base_url` / `llm_api_key` 时走确定性 mock（分类/改写/生成均可离线测试）；
配置后调用 OpenAI 兼容 `/chat/completions`（预留钩子，见 `_classify_remote` 等）。
"""
from __future__ import annotations

import json

import httpx

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


def _parse_json(content: str) -> dict[str, Any]:
    """把 LLM 输出解析为 dict；JSON 直接解析，否则抽取首个 `{...}` 片段再解析，失败返回空 dict。"""
    text = (content or "").strip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {}


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

    # ---------- 真实 API 钩子（OpenAI 兼容 /chat/completions） ----------

    def _chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        """调用 OpenAI 兼容 `/chat/completions`，返回首个 choice 的文本。"""
        payload: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        resp = httpx.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data["choices"][0]["message"].get("content") or "").strip()

    def _classify_remote(self, question: str) -> str:
        content = self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是 HR 助手的意图分类器。判断用户问题是否需要检索企业知识库"
                        "（制度/政策/流程/报销/请假/福利等）才能准确回答。只输出一个词：KB 或 GENERAL。"
                    ),
                },
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=8,
        )
        return "GENERAL" if "GENERAL" in content.upper() else "KB"

    def _rewrite_remote(self, question: str) -> dict[str, Any]:
        content = self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是查询改写器。把用户问题改写为适合在企业知识库中检索的简洁查询，"
                        "并提取不超过 6 个检索关键词。只输出 JSON："
                        '{"rewritten_query": "改写后的查询", "expanded_keywords": ["关键词1", "关键词2"]}'
                    ),
                },
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=300,
        )
        data = _parse_json(content)
        rewritten = str(data.get("rewritten_query") or question).strip() or question
        keywords = data.get("expanded_keywords")
        if not isinstance(keywords, list):
            keywords = extract_keywords(question, limit=6)
        else:
            keywords = [str(k) for k in keywords if str(k).strip()][:6]
        return {"rewritten_query": rewritten, "expanded_keywords": keywords}

    def _generate_remote(self, question: str, chunks: list[dict]) -> str:
        if not chunks:
            return ""
        context = "\n\n".join(
            f"【来源：{c.get('document_name', '文档')}】{c.get('chunk_text', '')}"
            for c in chunks
        )
        return self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是企业 HR 智能助手。只依据给定的参考资料回答，不要编造资料中没有的内容；"
                        "资料不足以回答时明确说明。回答使用简体中文，简洁准确。"
                    ),
                },
                {"role": "user", "content": f"问题：{question}\n\n参考资料：\n{context}"},
            ],
            temperature=0.3,
            max_tokens=800,
        )


# 服务层共享的默认客户端
llm_client = LLMClient()
