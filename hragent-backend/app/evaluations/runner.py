"""评测运行器（doc 42 §6.4）：统一跑三套 L3 测试集并聚合指标。

供 `run_evals.py` CLI 与 L3 pytest 测试共用，保证套级阈值与整体加权口径一致。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.evaluations import eval_utils as eu
from app.evaluations.agent_eval import AgentEvaluator
from app.evaluations.dify_eval import DifyEvaluator
from app.evaluations.rag_eval import RagEvaluator

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent  # hragent-backend
EVALS_DIR = BACKEND_ROOT / "evals"

SUITE_THRESHOLDS = {"agent": 0.90, "dify": 0.75, "rag": 0.70}
OVERALL_THRESHOLD = 0.85


async def run_suite(
    suite: str, user=None, knowledge_base_id=None, db=None
) -> dict[str, Any]:
    """跑单套测试集，返回 {suite,total,passed,pass_rate,by_category,metric_means}。"""
    samples = eu.load_golden(suite, EVALS_DIR)
    if suite == "agent":
        evaluator = AgentEvaluator()
    elif suite == "dify":
        evaluator = DifyEvaluator()
    else:
        evaluator = RagEvaluator(user=user, knowledge_base_id=knowledge_base_id, db=db)
    results = await evaluator.evaluate(samples)
    m = eu.compute_metrics([r.as_dict() for r in results])
    return {
        "suite": suite,
        "total": m["total"],
        "passed": m["passed"],
        "pass_rate": m["pass_rate"],
        "by_category": m["by_category"],
        "metric_means": m["metric_means"],
    }


async def run_l3(
    suites=("agent", "dify", "rag"), user=None, knowledge_base_id=None, db=None
) -> dict[str, Any]:
    """跑三套 L3，返回 {suites:{...}, overall:{total,passed,pass_rate}}（按样本量加权）。"""
    per_suite: dict[str, dict[str, Any]] = {}
    for suite in suites:
        per_suite[suite] = await run_suite(suite, user, knowledge_base_id, db)
    total = sum(v["total"] for v in per_suite.values())
    passed = sum(v["passed"] for v in per_suite.values())
    overall = {
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 1.0,
    }
    return {"suites": per_suite, "overall": overall}
