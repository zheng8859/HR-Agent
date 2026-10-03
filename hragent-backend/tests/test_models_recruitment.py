"""招聘四环节外键闭环测试（任务 6.1）：JD → 评分标准 → 简历评估 → 面试方案。"""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    InterviewPlan,
    JobDescription,
    ResumeEvaluation,
    ResumeEvaluationStatus,
    ScoringCriteria,
)


async def test_recruitment_four_chain_fk_closed_loop(db_session):
    jd = JobDescription(title="后端工程师", department="研发")
    db_session.add(jd)
    await db_session.flush()

    sc = ScoringCriteria(title="后端评分标准", job_description_id=jd.id)
    db_session.add(sc)
    await db_session.flush()

    re_ = ResumeEvaluation(
        candidate_name="张三",
        job_description_id=jd.id,
        scoring_criteria_id=sc.id,
        status=ResumeEvaluationStatus.interview.value,
    )
    db_session.add(re_)
    await db_session.flush()

    ip = InterviewPlan(candidate_name="张三", resume_evaluation_id=re_.id)
    db_session.add(ip)
    await db_session.flush()

    # 外键闭环断言
    assert sc.job_description_id == jd.id
    assert re_.job_description_id == jd.id
    assert re_.scoring_criteria_id == sc.id
    assert ip.resume_evaluation_id == re_.id


async def test_interview_plan_requires_evaluation_not_null(db_session):
    ip = InterviewPlan(candidate_name="李四", resume_evaluation_id=None)
    db_session.add(ip)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_interview_plan_requires_existing_evaluation(db_session):
    ip = InterviewPlan(candidate_name="李四", resume_evaluation_id=uuid.uuid4())
    db_session.add(ip)
    with pytest.raises(IntegrityError):
        await db_session.flush()
