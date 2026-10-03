"""统计看板服务：概览计数/环比、近 N 天趋势、最近活动（doc 41 §统计看板）。

计数口径（见 openspec stats-admin design.md）：
- 概览卡 = 各实体总数；环比 = 近 30 天与前一 30 天的增减量。
- 待处理面试数 = resume_evaluations 中 status == 'interview' 的记录数。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, InterviewPlan, JobDescription, ResumeEvaluation

_OVERVIEW_MODELS = [
    ("jd", "岗位描述", JobDescription),
    ("resume", "简历评估", ResumeEvaluation),
    ("interview", "面试方案", InterviewPlan),
    ("conversation", "对话", Conversation),
]

_SERIES_MODELS = [
    ("jd", JobDescription),
    ("resume", ResumeEvaluation),
    ("interview", InterviewPlan),
    ("conversation", Conversation),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _count(db: AsyncSession, model, where=None) -> int:
    stmt = select(func.count()).select_from(model)
    if where is not None:
        stmt = stmt.where(where)
    return (await db.execute(stmt)).scalar_one()


async def _growth(db: AsyncSession, model) -> int:
    now = _now()
    cur = await _count(db, model, model.created_at >= now - timedelta(days=30))
    prev = await _count(
        db,
        model,
        (model.created_at >= now - timedelta(days=60))
        & (model.created_at < now - timedelta(days=30)),
    )
    return cur - prev


async def dashboard_stats(db: AsyncSession) -> dict:
    now = _now()

    overview = []
    for key, label, model in _OVERVIEW_MODELS:
        total = await _count(db, model)
        growth = await _growth(db, model)
        overview.append({"key": key, "label": label, "value": total, "growth": growth})

    return {
        "overview": overview,
        "recruitment": {
            "resume_evaluation_total": await _count(db, ResumeEvaluation),
            "resume_evaluation_recent": await _count(
                db,
                ResumeEvaluation,
                ResumeEvaluation.created_at >= now - timedelta(days=30),
            ),
            "pending_interview_count": await _count(
                db, ResumeEvaluation, ResumeEvaluation.status == "interview"
            ),
            "interview_plan_total": await _count(db, InterviewPlan),
        },
        "conversation": {
            "conversation_total": await _count(db, Conversation),
            "conversation_recent": await _count(
                db, Conversation, Conversation.created_at >= now - timedelta(days=30)
            ),
        },
    }


async def trend_data(db: AsyncSession, days: int = 30) -> dict:
    now = _now()
    start = now - timedelta(days=days)
    start_date = start.date()

    series: dict[str, list[int]] = {}
    for key, model in _SERIES_MODELS:
        day_col = func.date_trunc("day", model.created_at)
        rows = (
            await db.execute(
                select(day_col.label("day"), func.count())
                .where(model.created_at >= start)
                .group_by(day_col)
            )
        ).all()
        by_day: dict = {}
        for day_dt, cnt in rows:
            d = day_dt.date() if isinstance(day_dt, datetime) else day_dt
            by_day[d] = int(cnt)
        series[key] = [
            by_day.get(start_date + timedelta(days=i), 0) for i in range(days)
        ]

    days_list = [(start_date + timedelta(days=i)).isoformat() for i in range(days)]
    return {"days": days_list, "series": series}


def _activity_title(record, typ: str) -> str:
    if typ == "jd":
        return record.title or "岗位描述"
    if typ == "resume":
        return record.candidate_name or record.original_filename or "简历评估"
    if typ == "interview":
        return record.candidate_name or "面试方案"
    return record.title or "对话"


async def recent_activities(db: AsyncSession, limit: int = 10) -> list[dict]:
    items: list[dict] = []
    for typ, model in [
        ("jd", JobDescription),
        ("resume", ResumeEvaluation),
        ("interview", InterviewPlan),
        ("conversation", Conversation),
    ]:
        rows = (
            await db.execute(
                select(model).order_by(model.created_at.desc()).limit(limit)
            )
        ).scalars().all()
        for r in rows:
            items.append(
                {
                    "type": typ,
                    "id": str(r.id),
                    "title": _activity_title(r, typ),
                    "created_at": r.created_at,
                }
            )
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items[:limit]
