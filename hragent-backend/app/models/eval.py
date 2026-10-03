"""评测数据模型（doc 42）：Golden 样本与评测运行记录。"""
from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class GoldenSample(BaseModel):
    """Golden 测试样本：从 JSON 导入，原始样本存 payload（结构随套件而异）。"""

    __tablename__ = "golden_samples"

    sample_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    suite: Mapped[str] = mapped_column(
        String(16), index=True, nullable=False
    )  # agent / dify / rag
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)


class EvalRun(BaseModel):
    """一次评测运行的结果记录，支持基线对比。"""

    __tablename__ = "eval_runs"

    suite: Mapped[str] = mapped_column(
        String(16), index=True, nullable=False
    )  # agent / dify / rag / all
    tier: Mapped[str] = mapped_column(String(8), nullable=False)  # l1 / l2 / l3 / all
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_baseline: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
