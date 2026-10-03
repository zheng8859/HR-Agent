"""评测纯函数工具集（doc 42 §6.6）：确定性、无副作用、可单测。

覆盖：结构完整性、分值配平、关键词覆盖、语义相似度、检索指标（recall/hit/rank）、
生成指标（faithfulness/relevance/citation）、意图/路由/契约精确匹配、工具注册表边界、
SSE 事件构造、聚合指标（compute_metrics）、Golden 加载与校验。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.embedding_service import tokenize_text

# ---------- 契约常量（doc 16 §二/§三/§7 + doc 20 §四） ----------

# 意图枚举（注册表）：6 个本期工具 + 2 个清单外边界
INTENT_ENUM = (
    "jd",
    "jd_edit",
    "criteria_edit",
    "resume_screening",
    "interview_plan",
    "resource_delete",
)

# 本期工具注册表（doc 43 明确范围：招聘 4 + 编辑 2 + 删除 1）
TOOL_REGISTRY: dict[str, str] = {
    "jd": "生成 JD",
    "jd_edit": "编辑 JD",
    "criteria_edit": "编辑评分标准",
    "resume_screening": "简历评估",
    "interview_plan": "生成面试方案",
    "resource_delete": "删除资源",
}

# 清单外工具（本期不做，仅边界校验）
OUT_OF_SCOPE_TOOLS = ("email_notification", "exam_generate")

# Agent 返回契约必含字段（doc 16 §7.1）
AGENT_CONTRACT_FIELDS = (
    "message",
    "intent",
    "route",
    "steps",
    "artifacts",
    "suggestions",
    "requires_confirmation",
    "missing_fields",
)

# SSE 事件序列（doc 16 §7.3 / doc 20 §四）
SSE_CHAT_EVENTS = ("thinking", "plan", "delta", "final")
SSE_TASK_EVENTS = ("progress", "delta", "artifact", "final")
SSE_ERROR_EVENT = "error"


# ---------- 结构完整性 ----------


def structure_completeness(actual: str | list[str], required: list[str]) -> float:
    """必备章节覆盖率 ∈ [0,1]：actual 可为全文（子串命中）或章节名列表（精确命中）。"""
    if not required:
        return 1.0
    if isinstance(actual, str):
        hit = sum(1 for r in required if r in actual)
    else:
        actual_set = {str(a).strip() for a in actual if a}
        hit = sum(1 for r in required if r in actual_set)
    return hit / len(required)


# ---------- 分值配平 ----------


def score_sum_valid(
    dimensions: list[dict], total_score: float, key: str = "max_score"
) -> bool:
    """分值配平：维度分之和严格等于总分（容差 1e-9，只报告不修正）。"""
    s = sum(float(d.get(key, 0.0)) for d in dimensions)
    return abs(s - float(total_score)) < 1e-9


# ---------- 关键词覆盖 ----------


def keyword_match_ratio(text: str, keywords: list[str]) -> float:
    """关键词覆盖占比 ∈ [0,1]：生成内容命中要点关键词的比例（允许换表述，逐词命中）。"""
    if not keywords:
        return 1.0
    t = (text or "").lower()
    hit = sum(1 for k in keywords if k.lower() in t)
    return hit / len(keywords)


# ---------- 语义相似度 ----------


def semantic_similarity(a: str, b: str) -> float:
    """语义相似度（mock 为词面 Jaccard；真实 embedding 见 L3 慢速路径）。"""
    ta = set(tokenize_text(a or ""))
    tb = set(tokenize_text(b or ""))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ---------- 检索指标 ----------


def retrieval_recall(retrieved_ids: list, expected_ids: list) -> float:
    """检索召回率：期望文档被命中的比例 ∈ [0,1]。"""
    if not expected_ids:
        return 1.0
    got = set(retrieved_ids)
    return sum(1 for e in expected_ids if e in got) / len(expected_ids)


def retrieval_hit_at_k(ranked_ids: list, expected_ids: list, k: int) -> float:
    """命中@k：前 k 个结果中是否命中任一期望文档（0/1）。"""
    top = set(ranked_ids[:k])
    return 1.0 if any(e in top for e in expected_ids) else 0.0


def retrieval_rank(ranked_ids: list, expected_ids: list) -> float:
    """平均倒数排名（MRR）：期望文档排名倒数的均值 ∈ [0,1]。"""
    if not expected_ids:
        return 1.0
    total = 0.0
    for e in expected_ids:
        for i, r in enumerate(ranked_ids, start=1):
            if r == e:
                total += 1.0 / i
                break
    return total / len(expected_ids)


# ---------- 生成指标 ----------


def faithfulness(answer: str, source_texts: list[str]) -> float:
    """忠实度 ∈ [0,1]：回答词项在来源片段中的覆盖占比（防幻觉）。"""
    if not answer or not answer.strip():
        return 1.0 if not source_texts else 0.0
    tokens = set(tokenize_text(answer))
    if not tokens:
        return 1.0
    corpus = " ".join(source_texts).lower()
    hit = sum(1 for t in tokens if t in corpus)
    return hit / len(tokens)


def relevance(answer: str, question: str) -> float:
    """相关性 ∈ [0,1]：回答与问题的语义相似度。"""
    return semantic_similarity(answer, question)


def citation_accuracy(citations: list[str], source_texts: list[str]) -> float:
    """引用准确率 ∈ [0,1]：引用片段确属来源的比例。"""
    if not citations:
        return 1.0
    corpus = " ".join(source_texts)
    hit = sum(1 for c in citations if (c or "").strip() in corpus)
    return hit / len(citations)


# ---------- 意图 / 路由 / 契约精确匹配 ----------


def exact_match(actual: Any, expected: Any) -> bool:
    """精确匹配：意图/路由为枚举，须精确相等（strip 归一）。"""
    a = (actual or "").strip() if isinstance(actual, str) else actual
    e = (expected or "").strip() if isinstance(expected, str) else expected
    return a == e


def intent_match(actual: str, expected: str) -> bool:
    return exact_match(actual, expected)


def route_match(actual: str, expected: str) -> bool:
    return exact_match(actual, expected)


def contract_fields_complete(
    present: list[str], required: list[str] | None = None
) -> bool:
    """契约字段齐全：Agent 返回必含 required（默认 AGENT_CONTRACT_FIELDS）。"""
    required = list(required) if required else list(AGENT_CONTRACT_FIELDS)
    present_set = set(present)
    return all(f in present_set for f in required)


def missing_fields_match(actual: list[str], expected: list[str]) -> float:
    """缺口识别命中率 ∈ [0,1]：期望缺失字段被正确识别出的比例。"""
    if not expected:
        return 1.0 if not actual else 0.0
    if not actual:
        return 0.0
    got = set(actual)
    return sum(1 for e in expected if e in got) / len(expected)


def requires_confirmation_match(actual: bool, expected: bool) -> bool:
    return bool(actual) == bool(expected)


# ---------- 工具注册表边界 ----------


def is_registered_tool(name: str) -> bool:
    return name in TOOL_REGISTRY


def is_out_of_scope_tool(name: str) -> bool:
    return name in OUT_OF_SCOPE_TOOLS


# ---------- SSE 事件构造 ----------


def build_sse_event(event_type: str, data: dict) -> str:
    """构造单条 SSE 事件帧（event + data，JSON 序列化）。"""
    valid = (*SSE_CHAT_EVENTS, *SSE_TASK_EVENTS, SSE_ERROR_EVENT)
    if event_type not in valid:
        raise ValueError(f"非法 SSE 事件类型: {event_type}")
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


def sse_event_sequence_complete(events: list[str], task_mode: bool = False) -> bool:
    """校验事件序列完整：对话 thinking→plan→delta→final；任务 progress→delta→artifact→final。

    按顺序子序列匹配，允许中间插入额外事件（如 progress）。
    """
    required = SSE_TASK_EVENTS if task_mode else SSE_CHAT_EVENTS
    it = iter(events)
    return all(any(e == r for e in it) for r in required)


# ---------- 聚合指标 ----------


def compute_metrics(results: list[dict]) -> dict:
    """聚合多样本结果：总通过率 + 分分类通过率 + 指标均值。"""
    total = len(results)
    if total == 0:
        return {"total": 0, "passed": 0, "pass_rate": 1.0, "by_category": {}, "metric_means": {}}
    passed = sum(1 for r in results if r.get("passed", False))
    by_category: dict[str, dict] = {}
    metric_sums: dict[str, float] = {}
    metric_counts: dict[str, int] = {}
    for r in results:
        cat = r.get("category") or "default"
        c = by_category.setdefault(cat, {"total": 0, "passed": 0})
        c["total"] += 1
        if r.get("passed"):
            c["passed"] += 1
        for k, v in (r.get("metrics") or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                metric_sums[k] = metric_sums.get(k, 0.0) + float(v)
                metric_counts[k] = metric_counts.get(k, 0) + 1
    by_category = {
        k: {**v, "pass_rate": v["passed"] / v["total"]} for k, v in by_category.items()
    }
    metric_means = {
        k: metric_sums[k] / metric_counts[k] for k in metric_sums if metric_counts[k]
    }
    return {
        "total": total,
        "passed": passed,
        "pass_rate": passed / total,
        "by_category": by_category,
        "metric_means": metric_means,
    }


# ---------- Golden 加载与校验 ----------


def load_golden(suite: str, base_dir: str | Path) -> list[dict]:
    """从 base_dir/<suite>_cases/*.json 加载全部样本（每文件可为数组或单对象，平铺）。"""
    root = Path(base_dir) / f"{suite}_cases"
    samples: list[dict] = []
    if not root.exists():
        return samples
    for f in sorted(root.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else [data]
        samples.extend(items)
    return samples


def validate_sample(sample: dict, suite: str) -> list[str]:
    """轻量结构校验，返回错误列表（空 = 合法）。"""
    errors: list[str] = []
    sid = sample.get("id")
    if not isinstance(sid, str) or not sid:
        errors.append("id 必须为非空字符串")
    expected_layer = {"agent": "agent", "dify": "content", "rag": "rag"}.get(suite)
    if sample.get("layer") != expected_layer:
        errors.append(f"layer 应为 {expected_layer!r}")
    if sample.get("eval_type") != suite:
        errors.append(f"eval_type 应为 {suite!r}")
    if "input" not in sample:
        errors.append("缺少 input")
    if suite == "dify":
        if "expected_output" not in sample:
            errors.append("dify 样本缺少 expected_output")
    else:
        if "expected" not in sample:
            errors.append(f"{suite} 样本缺少 expected")
    return errors
