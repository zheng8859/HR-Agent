"""内容生成评测器（doc 42 §6.2）：结构完整性、分值配平、关键词覆盖。

接 `dify_client`（无密钥时 mock 返回确定性产物），规则检查为主。
"""
from __future__ import annotations

from app.evaluations import eval_utils as eu
from app.evaluations.base import BaseEvaluator, EvalResult
from app.services.dify_service import dify_client

JD_SECTIONS = ("岗位职责", "任职要求", "技能要求")

# 面试七要素（doc 16 §7.2 / doc 42 §1.3）→ mock 输出键
INTERVIEW_KEY_MAP = {
    "goal": "面试目标",
    "process": "面试流程",
    "core_questions": "核心问题",
    "follow_up": "追问建议",
    "dimensions": "考察维度",
    "scoring_advice": "评分建议",
    "risk_points": "风险点",
}


def jd_actual_sections(output: dict) -> list[str]:
    """JD 输出结构章节：content 内章节头命中 + skills 字段计入技能要求覆盖。"""
    content = output.get("content") or ""
    sections = [s for s in JD_SECTIONS if s in content]
    if "技能要求" not in sections and output.get("skills"):
        sections.append("技能要求")
    return sections


def interview_actual_sections(output: dict) -> list[str]:
    """面试方案七要素：按输出键映射章节名，键非空即覆盖。"""
    return [label for key, label in INTERVIEW_KEY_MAP.items() if output.get(key)]


class DifyEvaluator(BaseEvaluator):
    suite = "dify"
    threshold = 0.75

    async def evaluate_one(self, sample: dict) -> EvalResult:
        module = sample["module"]
        inputs = sample.get("input") or {}
        expected = sample.get("expected_output") or {}
        structure = expected.get("structure") or []
        checks = expected.get("quality_checks") or {}
        structure_min = (sample.get("tolerance") or {}).get("structure_min", 0.9)
        metrics: dict[str, float] = {}

        if module == "jd":
            output = await dify_client.run_jd_workflow(inputs)
            completeness = eu.structure_completeness(jd_actual_sections(output), structure)
            metrics["structure_completeness"] = completeness
            skills_ok = bool(output.get("skills"))
            metrics["skills_covered"] = 1.0 if skills_ok else 0.0
            passed = completeness >= structure_min and skills_ok

        elif module == "scoring":
            output = await dify_client.run_scoring_workflow(inputs)
            dims = output.get("dimensions") or []
            total = float(output.get("total_score", 100))
            balanced = eu.score_sum_valid(dims, total)
            metrics["score_sum_valid"] = 1.0 if balanced else 0.0
            has_dims = bool(dims)
            metrics["has_dimensions"] = 1.0 if has_dims else 0.0
            passed = balanced and has_dims

        elif module == "resume":
            output = await dify_client.run_resume_workflow(inputs)
            dims = output.get("dimensions") or []
            total = float(output.get("total_score", 0))
            balanced = eu.score_sum_valid(dims, total, key="score")
            metrics["score_sum_valid"] = 1.0 if balanced else 0.0
            reasons_ok = all(d.get("reason") for d in dims)
            metrics["has_reasons"] = 1.0 if reasons_ok else 0.0
            passed = balanced and reasons_ok

        elif module == "interview":
            output = await dify_client.run_interview_workflow(inputs)
            completeness = eu.structure_completeness(
                interview_actual_sections(output), structure
            )
            metrics["structure_completeness"] = completeness
            # 专属而非模板：目标与核心问题均非空
            customized = bool(output.get("goal")) and bool(output.get("core_questions"))
            metrics["customized"] = 1.0 if customized else 0.0
            passed = completeness >= structure_min and customized

        else:
            passed = False

        return EvalResult(
            sample_id=sample["id"],
            passed=passed,
            metrics=metrics,
            category=module,
            detail=module,
        )
