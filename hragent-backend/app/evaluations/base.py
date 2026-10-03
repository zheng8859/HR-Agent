"""评测器基类（doc 42 §6.2）：结果结构与统一评测入口。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalResult:
    """单样本评测结果。"""

    sample_id: str
    passed: bool
    metrics: dict[str, float] = field(default_factory=dict)
    category: str = ""
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "passed": self.passed,
            "category": self.category,
            "metrics": self.metrics,
            "detail": self.detail,
        }


class BaseEvaluator:
    """评测器基类：suite 与套级阈值（红线）。"""

    suite: str = ""
    threshold: float = 0.0

    def __init__(self, mock: bool = True) -> None:
        self.mock = mock

    async def evaluate_one(self, sample: dict) -> EvalResult:
        raise NotImplementedError

    async def evaluate(self, samples: list[dict]) -> list[EvalResult]:
        results: list[EvalResult] = []
        for sample in samples:
            results.append(await self.evaluate_one(sample))
        return results
