"""Agent 编排评测器（doc 42 §6.2）：意图匹配、契约检查、确认判定、工具边界。

doc 43 起，快通道规范实现收敛到 `app.services.intent_service.classify_intent_fast`；
本评测器直接引用同一函数（不再维护「参考规则」副本），保证评测与实现永不漂移。
"""
from __future__ import annotations

from app.evaluations import eval_utils as eu
from app.evaluations.base import BaseEvaluator, EvalResult
from app.services.intent_service import classify_intent_fast


class AgentEvaluator(BaseEvaluator):
    """Agent 编排评测器：规则检查为主，语义裁判挂点见 _llm_judge。"""

    suite = "agent"
    threshold = 0.90

    async def evaluate_one(self, sample: dict) -> EvalResult:
        actual = classify_intent_fast(
            sample["input"]["message"], sample["input"].get("attachments")
        )
        expected = sample.get("expected") or {}
        metrics: dict[str, float] = {}

        intent_ok = eu.intent_match(actual["intent"], expected.get("intent"))
        metrics["intent_match"] = 1.0 if intent_ok else 0.0

        route_ok = eu.route_match(actual["route"], expected.get("route"))
        metrics["route_match"] = 1.0 if route_ok else 0.0

        confirm_ok = eu.requires_confirmation_match(
            actual["requires_confirmation"], expected.get("requires_confirmation", False)
        )
        metrics["requires_confirmation"] = 1.0 if confirm_ok else 0.0

        # 工具边界：期望工具须在注册表内（chat 无工具）
        expected_tool = expected.get("tool")
        tool_ok = True if not expected_tool else eu.is_registered_tool(expected_tool)
        metrics["tool_registered"] = 1.0 if tool_ok else 0.0

        mf_score = eu.missing_fields_match(
            actual["missing_fields"], expected.get("missing_fields") or []
        )
        metrics["missing_fields"] = mf_score

        passed = intent_ok and route_ok and confirm_ok and tool_ok
        detail = f"actual={actual['intent']} expected={expected.get('intent')}"
        return EvalResult(
            sample_id=sample["id"],
            passed=passed,
            metrics=metrics,
            category=sample.get("category", ""),
            detail=detail,
        )

    def _llm_judge(self, sample: dict, actual: dict) -> float:
        """LLM 语义裁判挂点（真实 L3 慢速路径预留）。mock 阶段不调用。"""
        return 1.0
