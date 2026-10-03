"""统计看板响应 schema（doc 41）。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OverviewCard(BaseModel):
    key: str
    label: str
    value: int
    growth: int | None = None


class RecruitmentStats(BaseModel):
    resume_evaluation_total: int
    resume_evaluation_recent: int
    pending_interview_count: int
    interview_plan_total: int


class ConversationStats(BaseModel):
    conversation_total: int
    conversation_recent: int


class DashboardResponse(BaseModel):
    overview: list[OverviewCard]
    recruitment: RecruitmentStats
    conversation: ConversationStats


class TrendResponse(BaseModel):
    days: list[str]
    series: dict[str, list[int]]


class ActivityItem(BaseModel):
    type: str
    id: str
    title: str
    created_at: datetime
