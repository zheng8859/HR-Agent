"""种子脚本（doc 42 §6.1）：将 Golden JSON 样本导入 golden_samples 表（幂等）。

用法：
    python scripts/seed_evals.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

# 使脚本可独立运行（从 backend 根目录执行）
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import async_session_factory  # noqa: E402
from app.evaluations import eval_utils as eu  # noqa: E402
from app.models import GoldenSample  # noqa: E402

SUITES = ("agent", "dify", "rag")


def _category(sample: dict, suite: str) -> str | None:
    return sample.get("category") or sample.get("module") or None


async def seed(db) -> dict:
    imported = 0
    for suite in SUITES:
        for sample in eu.load_golden(suite, BACKEND_ROOT / "evals"):
            existing = (
                await db.execute(
                    select(GoldenSample).where(GoldenSample.sample_id == sample["id"])
                )
            ).scalar_one_or_none()
            if existing:
                existing.suite = suite
                existing.category = _category(sample, suite)
                existing.payload = sample
                existing.tags = sample.get("tags") or []
            else:
                db.add(
                    GoldenSample(
                        sample_id=sample["id"],
                        suite=suite,
                        category=_category(sample, suite),
                        payload=sample,
                        tags=sample.get("tags") or [],
                    )
                )
            imported += 1
    await db.commit()
    return {"imported": imported, "suites": list(SUITES)}


async def main() -> None:
    async with async_session_factory() as db:
        result = await seed(db)
    print(f"Golden 样本导入完成：{result['imported']} 个（agent 50 / dify 40 / rag 30）")


if __name__ == "__main__":
    asyncio.run(main())
