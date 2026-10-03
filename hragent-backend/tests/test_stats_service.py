"""统计看板服务测试：计数/环比/趋势/最近活动。"""
from datetime import datetime, timedelta, timezone

from app.models import Conversation, InterviewPlan, JobDescription, ResumeEvaluation
from app.services import stats_service


def _ago(days):
    return datetime.now(timezone.utc) - timedelta(days=days)


async def _make_jd(db_session, title, created_at=None):
    jd = JobDescription(title=title, status="draft")
    if created_at:
        jd.created_at = created_at
    db_session.add(jd)
    await db_session.flush()
    return jd


async def _make_resume(db_session, status="pending", created_at=None):
    r = ResumeEvaluation(status=status)
    if created_at:
        r.created_at = created_at
    db_session.add(r)
    await db_session.flush()
    return r


async def _make_interview(db_session, resume, created_at=None):
    p = InterviewPlan(resume_evaluation_id=resume.id)
    if created_at:
        p.created_at = created_at
    db_session.add(p)
    await db_session.flush()
    return p


async def _make_conv(db_session, created_at=None):
    c = Conversation()
    if created_at:
        c.created_at = created_at
    db_session.add(c)
    await db_session.flush()
    return c


async def test_dashboard_counts_and_growth(db_session):
    # 近 30 天 2 条 JD，前 30 天 1 条 JD → 环比 +1
    await _make_jd(db_session, "JD-A", _ago(5))
    await _make_jd(db_session, "JD-B", _ago(10))
    await _make_jd(db_session, "JD-C", _ago(40))
    await _make_resume(db_session, "interview", _ago(2))
    await _make_resume(db_session, "pending", _ago(2))
    await _make_resume(db_session, "pending", _ago(40))
    r = await _make_resume(db_session, "interview", _ago(3))
    await _make_interview(db_session, r, _ago(1))
    await _make_conv(db_session, _ago(1))
    await _make_conv(db_session, _ago(35))

    d = await stats_service.dashboard_stats(db_session)

    overview = {o["key"]: o for o in d["overview"]}
    assert overview["jd"]["value"] == 3
    assert overview["jd"]["growth"] == 1  # 2 - 1
    assert overview["resume"]["value"] == 4
    assert overview["interview"]["value"] == 1
    assert overview["conversation"]["value"] == 2

    assert d["recruitment"]["resume_evaluation_total"] == 4
    assert d["recruitment"]["resume_evaluation_recent"] == 3  # 近 30 天 3 条
    assert d["recruitment"]["pending_interview_count"] == 2  # status == interview
    assert d["recruitment"]["interview_plan_total"] == 1
    assert d["conversation"]["conversation_total"] == 2
    assert d["conversation"]["conversation_recent"] == 1


async def test_trend_series_sum(db_session):
    await _make_jd(db_session, "JD-1", _ago(1))
    await _make_jd(db_session, "JD-2", _ago(2))
    await _make_jd(db_session, "JD-3", _ago(3))
    await _make_conv(db_session, _ago(1))
    await _make_conv(db_session, _ago(2))

    t = await stats_service.trend_data(db_session, days=30)
    assert len(t["days"]) == 30
    assert len(t["series"]["jd"]) == 30
    assert sum(t["series"]["jd"]) == 3
    assert sum(t["series"]["conversation"]) == 2
    assert sum(t["series"]["interview"]) == 0


async def test_recent_activities_sorted_desc(db_session):
    await _make_jd(db_session, "JD-new", _ago(1))
    await _make_resume(db_session, "pending", _ago(2))
    await _make_conv(db_session, _ago(3))

    acts = await stats_service.recent_activities(db_session, limit=10)
    assert len(acts) == 3
    assert {a["type"] for a in acts} == {"jd", "resume", "conversation"}
    times = [a["created_at"] for a in acts]
    assert times == sorted(times, reverse=True)
