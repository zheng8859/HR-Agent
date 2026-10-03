"""L3 质量评测（doc 42 §3.2 / §7）：agent/dify/rag 三套 Golden 测试集。

标记 `@pytest.mark.l3` + `@pytest.mark.slow`（真实 LLM 时慢速，无 key 走 mock）。
每个套级测试跑完把指标写到 `evals/reports/latest/l3_<suite>.json`，供 `run_evals.py`
聚合整体通过率与基线对比；套级阈值由 `runner.SUITE_THRESHOLDS` 定义。
"""
import json
from pathlib import Path

import pytest

from app.evaluations.runner import SUITE_THRESHOLDS, run_suite

REPORTS_DIR = Path(__file__).resolve().parent.parent / "evals" / "reports" / "latest"

pytestmark = [pytest.mark.l3, pytest.mark.slow]


def _write_report(suite: str, result: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"l3_{suite}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@pytest.mark.suite_agent
async def test_l3_agent_suite():
    result = await run_suite("agent")
    _write_report("agent", result)
    assert result["pass_rate"] >= SUITE_THRESHOLDS["agent"], (
        f"agent 套通过率 {result['pass_rate']:.2%} 低于红线 {SUITE_THRESHOLDS['agent']:.0%}"
    )


@pytest.mark.suite_dify
async def test_l3_dify_suite():
    result = await run_suite("dify")
    _write_report("dify", result)
    assert result["pass_rate"] >= SUITE_THRESHOLDS["dify"], (
        f"dify 套通过率 {result['pass_rate']:.2%} 低于红线 {SUITE_THRESHOLDS['dify']:.0%}"
    )


@pytest.mark.suite_rag
async def test_l3_rag_suite(db_session, eval_user, eval_kb):
    result = await run_suite("rag", user=eval_user, knowledge_base_id=eval_kb.id, db=db_session)
    _write_report("rag", result)
    assert result["pass_rate"] >= SUITE_THRESHOLDS["rag"], (
        f"rag 套通过率 {result['pass_rate']:.2%} 低于红线 {SUITE_THRESHOLDS['rag']:.0%}"
    )
