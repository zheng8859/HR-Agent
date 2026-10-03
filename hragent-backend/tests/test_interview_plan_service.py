"""面试方案服务单元测试：守卫、候选人四态、三要素、状态联动、导出、重新生成、所有权。"""
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models import JobDescription, ResumeEvaluation, ResumeEvaluationStatus, User
from app.schemas.interview_plan import InterviewPlanGenerateRequest
from app.services import interview_plan_service as svc


async def _make_user(db_session, username="hr", role="hr_manager"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="x",
        role=role,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_jd(db_session):
    jd = JobDescription(title="前端开发工程师", content="负责前端页面开发")
    db_session.add(jd)
    await db_session.flush()
    return jd


async def _make_evaluation(db_session, user, jd, name="张三", total_score=78.0):
    ev = ResumeEvaluation(
        candidate_name=name,
        candidate_position="前端开发工程师",
        resume_content="五年前端经验，精通 Vue/TypeScript",
        total_score=total_score,
        evaluation_metrics=[{"name": "学历匹配度", "score": 16, "max": 20, "reason": "本科"}],
        status=ResumeEvaluationStatus.pending.value,
        job_description_id=jd.id,
        user_id=user.id,
    )
    db_session.add(ev)
    await db_session.flush()
    return ev


# ---------- 候选人解析四态 ----------


def _cand(name):
    return SimpleNamespace(candidate_name=name)


def test_resolve_candidate_no_specific():
    assert svc.resolve_candidate("", [_cand("张三")]).state == "no_specific"


def test_resolve_candidate_no_match():
    assert svc.resolve_candidate("李四", [_cand("张三")]).state == "no_match"


def test_resolve_candidate_matched():
    r = svc.resolve_candidate("张三", [_cand("张三"), _cand("李四")])
    assert r.state == "matched"
    assert len(r.matches) == 1


def test_resolve_candidate_ambiguous():
    r = svc.resolve_candidate("张", [_cand("张三"), _cand("张伟")])
    assert r.state == "ambiguous"
    assert len(r.matches) == 2


# ---------- 三要素结构 ----------


def test_format_plan_contains_three_sections():
    content = svc.format_plan(
        {
            "goal": "目标",
            "process": "流程",
            "core_questions": ["问题一", "问题二"],
        }
    )
    for header in svc.INTERVIEW_SECTION_TITLES:
        assert header in content


# ---------- 生成守卫 ----------


async def test_generate_missing_evaluation_404(db_session):
    user = await _make_user(db_session)
    with pytest.raises(HTTPException) as e:
        await svc.generate_plan(
            InterviewPlanGenerateRequest(resume_evaluation_id=uuid.uuid4()),
            user,
            db_session,
        )
    assert e.value.status_code == 404


async def test_generate_unscored_evaluation_422(db_session):
    user = await _make_user(db_session)
    jd = await _make_jd(db_session)
    ev = await _make_evaluation(db_session, user, jd, total_score=None)
    with pytest.raises(HTTPException) as e:
        await svc.generate_plan(
            InterviewPlanGenerateRequest(resume_evaluation_id=ev.id),
            user,
            db_session,
        )
    assert e.value.status_code == 422


# ---------- 生成 / 状态联动 / 重新生成 / 导出 / 所有权 ----------


async def test_generate_creates_plan_and_links_status(db_session):
    user = await _make_user(db_session)
    jd = await _make_jd(db_session)
    ev = await _make_evaluation(db_session, user, jd)

    plan = await svc.generate_plan(
        InterviewPlanGenerateRequest(resume_evaluation_id=ev.id), user, db_session
    )
    assert plan.resume_evaluation_id == ev.id
    assert plan.user_id == user.id
    for header in svc.INTERVIEW_SECTION_TITLES:
        assert header in plan.content
    assert ev.status == ResumeEvaluationStatus.interview.value


async def test_regenerate_updates_content_and_keeps_status(db_session):
    user = await _make_user(db_session)
    jd = await _make_jd(db_session)
    ev = await _make_evaluation(db_session, user, jd)
    plan = await svc.generate_plan(
        InterviewPlanGenerateRequest(resume_evaluation_id=ev.id), user, db_session
    )

    regen = await svc.regenerate_plan(plan.id, user, db_session)
    assert regen.id == plan.id
    for header in svc.INTERVIEW_SECTION_TITLES:
        assert header in regen.content
    assert ev.status == ResumeEvaluationStatus.interview.value


async def test_export_plan_markdown(db_session):
    user = await _make_user(db_session)
    jd = await _make_jd(db_session)
    ev = await _make_evaluation(db_session, user, jd)
    plan = await svc.generate_plan(
        InterviewPlanGenerateRequest(resume_evaluation_id=ev.id), user, db_session
    )

    content = await svc.export_plan(plan.id, "md", user, db_session)
    for header in svc.INTERVIEW_SECTION_TITLES:
        assert header in content


async def test_ownership_isolation(db_session):
    owner = await _make_user(db_session, "owner")
    other = await _make_user(db_session, "other")
    jd = await _make_jd(db_session)
    ev = await _make_evaluation(db_session, owner, jd)
    plan = await svc.generate_plan(
        InterviewPlanGenerateRequest(resume_evaluation_id=ev.id), owner, db_session
    )

    with pytest.raises(HTTPException) as e:
        await svc.get_plan(plan.id, other, db_session)
    assert e.value.status_code == 404

    assert len(await svc.list_plans(other, db_session)) == 0
    assert len(await svc.list_plans(owner, db_session)) == 1
