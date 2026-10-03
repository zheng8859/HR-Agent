"""Evals CLI 运行器（doc 42 §6.4）：分层运行评测 + HTML 报告 + 基线对比。

用法：
    python scripts/run_evals.py --tier all --run-slow
    python scripts/run_evals.py --tier l3 --suite rag
    python scripts/run_evals.py --tier all --run-slow --save-baseline
    python scripts/run_evals.py --tier all --run-slow --compare evals/baseline.json
    python scripts/run_evals.py --tier all --run-slow --output evals/reports/evals.html

L1/L2 走 pytest（标记 l1/l2），L3 走 pytest 标记 l3 + slow（测试体内部把套级指标写到
evals/reports/latest/l3_<suite>.json），本脚本读取后聚合整体通过率与基线对比。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = BACKEND_ROOT / "evals"
LATEST_DIR = EVALS_DIR / "reports" / "latest"
BASELINE_FILE = EVALS_DIR / "baseline.json"

THRESHOLDS = {"l1": 0.95, "l2": 0.90, "l3": 0.85}
SUITE_THRESHOLDS = {"agent": 0.90, "dify": 0.75, "rag": 0.70}
SUITES = ("agent", "dify", "rag")


# ---------- pytest 运行 ----------


def _marker_expr(tier: str, suite: str | None, run_slow: bool) -> str:
    if tier == "l3":
        expr = "l3" if run_slow else "l3 and not slow"
        if suite:
            expr = f"({expr}) and suite_{suite}"
        return expr
    return tier


def run_pytest(tier: str, suite: str | None, run_slow: bool) -> dict[str, int]:
    """跑某一层测试，返回 {passed, failed}（来自 pytest-json-report）。"""
    report_file = LATEST_DIR / f"pytest_{tier}.json"
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        _marker_expr(tier, suite, run_slow),
        "--json-report",
        f"--json-report-file={report_file}",
        "-q",
    ]
    proc = subprocess.run(cmd, cwd=str(BACKEND_ROOT), capture_output=False)
    if not report_file.exists():
        return {"passed": 0, "failed": 0}
    data = json.loads(report_file.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0) + summary.get("error", 0)
    return {"passed": passed, "failed": failed}


# ---------- L3 套级指标 ----------


def read_l3_suites() -> dict[str, dict[str, Any]]:
    suites: dict[str, dict[str, Any]] = {}
    for s in SUITES:
        f = LATEST_DIR / f"l3_{s}.json"
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            suites[s] = {
                "total": d.get("total", 0),
                "passed": d.get("passed", 0),
                "pass_rate": d.get("pass_rate", 0.0),
            }
    return suites


def _tier_result(passed: int, failed: int) -> dict[str, Any]:
    total = passed + failed
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total else 1.0,
    }


# ---------- 报告 ----------


def build_html(results: dict) -> str:
    def color(rate: float, threshold: float) -> str:
        if rate >= threshold:
            return "#27ae60"  # green
        if rate >= threshold - 0.05:
            return "#f39c12"  # amber
        return "#e74c3c"  # red

    rows = []
    for tier, t in results["tiers"].items():
        rows.append(
            f"<tr><td>{tier.upper()}</td><td>{t['passed']}/{t['total']}</td>"
            f"<td style='color:{color(t['pass_rate'], t['threshold'])}'>{t['pass_rate']:.1%}</td>"
            f"<td>{t['threshold']:.0%}</td></tr>"
        )
        if tier == "l3":
            for s, d in t.get("suites", {}).items():
                rows.append(
                    f"<tr><td>&nbsp;&nbsp;└ {s}</td><td>{d['passed']}/{d['total']}</td>"
                    f"<td style='color:{color(d['pass_rate'], SUITE_THRESHOLDS[s])}'>{d['pass_rate']:.1%}</td>"
                    f"<td>{SUITE_THRESHOLDS[s]:.0%}</td></tr>"
                )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Evals 评测报告</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:720px;margin:32px auto;padding:0 16px;color:#222}}
table{{border-collapse:collapse;width:100%}}
th,td{{border-bottom:1px solid #ddd;padding:10px 12px;text-align:left}}
th{{background:#f5f5f5}}
h1{{font-size:1.4em}} .muted{{color:#888;font-size:.85em}}
</style></head><body>
<h1>Evals 评测报告 <span class="muted">{results['generated_at']}</span></h1>
<table><tr><th>层级 / 套</th><th>通过</th><th>通过率</th><th>红线</th></tr>
{''.join(rows)}
</table></body></html>"""


def compare_with_baseline(current: dict, baseline: dict) -> list[dict]:
    """逐层对比，返回劣化记录（pass_rate 下降 > 5%）。"""
    regressions = []
    for tier, t in current["tiers"].items():
        b = baseline.get("tiers", {}).get(tier)
        if not b or not b.get("total"):
            continue
        delta = t["pass_rate"] - b["pass_rate"]
        if delta < -0.05:
            regressions.append({"tier": tier, "delta": delta, "current": t["pass_rate"], "baseline": b["pass_rate"]})
    return regressions


def collect(tiers: list[str], suite: str | None, run_slow: bool) -> dict:
    results: dict[str, Any] = {"generated_at": datetime.now(timezone.utc).isoformat(), "tiers": {}}
    for tier in tiers:
        if tier in ("l1", "l2"):
            counts = run_pytest(tier, None, run_slow)
            results["tiers"][tier] = {**_tier_result(counts["passed"], counts["failed"]), "threshold": THRESHOLDS[tier]}
        else:  # l3
            counts = run_pytest("l3", suite, run_slow)
            suites = read_l3_suites() if not suite else {suite: json.loads(
                (LATEST_DIR / f"l3_{suite}.json").read_text(encoding="utf-8")
            ) if (LATEST_DIR / f"l3_{suite}.json").exists() else {}}
            total = sum(v["total"] for v in suites.values())
            passed = sum(v["passed"] for v in suites.values())
            results["tiers"]["l3"] = {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": passed / total if total else 1.0,
                "threshold": THRESHOLDS["l3"],
                "suites": suites,
                "pytest_passed": counts["passed"],
                "pytest_failed": counts["failed"],
            }
    return results


def main() -> int:
    # Windows 控制台默认 GBK，无法编码 ✓/✗/└ 等符号；统一按 UTF-8 输出（CI 与本地均稳定）
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Evals 评测运行器（doc 42 §6.4）")
    ap.add_argument("--tier", choices=["l1", "l2", "l3", "all"], default="all")
    ap.add_argument("--suite", choices=list(SUITES), default=None, help="仅 L3 生效：只跑某套测试集")
    ap.add_argument("--run-slow", action="store_true", help="允许 L3 慢速（真实 LLM）测试")
    ap.add_argument("--compare", type=Path, default=None, help="与历史基线对比并输出劣化报告")
    ap.add_argument("--save-baseline", action="store_true", help="保存当前结果为 evals/baseline.json")
    ap.add_argument("--output", type=Path, default=None, help="生成 HTML 单文件报告路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON 供 CI 集成")
    args = ap.parse_args()

    tiers = {"l1": ["l1"], "l2": ["l2"], "l3": ["l3"], "all": ["l1", "l2"] + (["l3"] if args.run_slow else [])}[args.tier]
    if not tiers:
        print("提示：--tier all 需搭配 --run-slow 才会运行 L3；或显式 --tier l3 --run-slow", file=sys.stderr)
        return 1

    results = collect(tiers, args.suite, args.run_slow)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    # 打印汇总
    for tier, t in results["tiers"].items():
        status = "✓" if t["pass_rate"] >= t["threshold"] else "✗"
        print(f"[{status}] {tier.upper():3s} {t['passed']}/{t['total']} ({t['pass_rate']:.1%}, 红线 {t['threshold']:.0%})")
        if tier == "l3":
            for s, d in t.get("suites", {}).items():
                ok = d["pass_rate"] >= SUITE_THRESHOLDS[s]
                print(f"      └ {s:6s} {d['passed']}/{d['total']} ({d['pass_rate']:.1%}, 红线 {SUITE_THRESHOLDS[s]:.0%}) {'✓' if ok else '✗'}")

    if args.save_baseline:
        BASELINE_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已保存基线 → {BASELINE_FILE}")

    if args.compare and args.compare.exists():
        baseline = json.loads(args.compare.read_text(encoding="utf-8"))
        regressions = compare_with_baseline(results, baseline)
        if regressions:
            print("⚠ 劣化检测（下降 > 5%）：")
            for r in regressions:
                print(f"  - {r['tier'].upper()}: {r['baseline']:.1%} → {r['current']:.1%} ({r['delta']:+.1%})")
        else:
            print("无劣化（各层下降均 ≤ 5%）")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(build_html(results), encoding="utf-8")
        print(f"HTML 报告 → {args.output}")

    # 整体是否达标（CI 退出码）
    ok = all(t["pass_rate"] >= t["threshold"] for t in results["tiers"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
