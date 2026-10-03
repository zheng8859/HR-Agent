"""Agent 技能 handler 单元测试（doc 44 §二/§六）：6 工具真实执行、前置缺口、产物类型、删除两步确认。"""
import pytest

from app.models import JobDescription, ResumeEvaluation, ScoringCriteria
from app.skills.agent_skills import AgentSkillDispatcher, ToolOutcome, skill_dispatcher


def _params(message, attachments=None):
    return {"message": message, "attachments": attachments or [], "memory": ""}


async def _seed_jd(db, title="前端工程师"):
    jd = JobDescription(title=title, content="岗位正文")
    db.add(jd)
    await db.flush()
    return jd


# ---------- 边界：清单外 intent ----------


async def test_dispatch_unregistered_raises(eval_user, db_session):
    with pytest.raises(ValueError):
        await skill_dispatcher.dispatch("email_draft", _params("x"), eval_user, db_session)


async def test_is_registered():
    assert skill_dispatcher.is_registered("jd") is True
    assert skill_dispatcher.is_registered("email_draft") is False


# ---------- jd（生成 JD） ----------


async def test_jd_missing_title_returns_requirements(eval_user, db_session):
    outcome = await skill_dispatcher.dispatch("jd", _params("帮我生成一份 JD"), eval_user, db_session)
    assert outcome.missing_fields == ["job_title"]
    assert outcome.artifacts[0]["type"] == "requirements"


async def test_jd_complete_returns_jd_confirm(eval_user, db_session):
    outcome = await skill_dispatcher.dispatch("jd", _params("生成前端工程师 JD"), eval_user, db_session)
    assert outcome.missing_fields == []
    art = outcome.artifacts[0]
    assert art["type"] == "jd_confirm"
    assert art["draft"]["title"] == "前端工程师"


# ---------- jd_edit / criteria_edit（编辑定位） ----------


async def test_jd_edit_no_target(eval_user, db_session):
    outcome = await skill_dispatcher.dispatch("jd_edit", _params("修改一下 JD"), eval_user, db_session)
    assert outcome.missing_fields == ["target"]


async def test_jd_edit_single_match(eval_user, db_session):
    jd = await _seed_jd(db_session)
    outcome = await skill_dispatcher.dispatch(
        "jd_edit", _params("修改前端工程师的 JD"), eval_user, db_session
    )
    assert outcome.artifacts[0]["type"] == "jd_edit_request"
    assert outcome.artifacts[0]["jd_id"] == str(jd.id)


async def test_jd_edit_multiple_candidates(eval_user, db_session):
    await _seed_jd(db_session, "前端工程师A")
    await _seed_jd(db_session, "前端工程师B")
    outcome = await skill_dispatcher.dispatch(
        "jd_edit", _params("修改前端工程师的 JD"), eval_user, db_session
    )
    assert outcome.artifacts[0]["type"] == "jd_edit_candidates"
    assert len(outcome.artifacts[0]["candidates"]) == 2


async def test_criteria_edit_single_match(eval_user, db_session):
    sc = ScoringCriteria(title="前端工程师 评分标准", content="正文")
    db_session.add(sc)
    await db_session.flush()
    outcome = await skill_dispatcher.dispatch(
        "criteria_edit", _params("修改前端工程师的评分标准"), eval_user, db_session
    )
    assert outcome.artifacts[0]["type"] == "criteria_edit_request"
    assert outcome.artifacts[0]["criteria_id"] == str(sc.id)


# ---------- resume_screening（简历评估引导） ----------


async def test_resume_screening_no_attachment(eval_user, db_session):
    outcome = await skill_dispatcher.dispatch(
        "resume_screening", _params("评估这份简历"), eval_user, db_session
    )
    assert outcome.missing_fields == ["resume_file"]
    assert outcome.artifacts[0]["type"] == "resume_upload_request"


async def test_resume_screening_with_attachment(eval_user, db_session):
    outcome = await skill_dispatcher.dispatch(
        "resume_screening", _params("评估这份简历", ["resume"]), eval_user, db_session
    )
    assert outcome.artifacts[0]["type"] == "resume_screening_results"


# ---------- interview_plan（候选人四态） ----------


def _seed_eval(db, user, name="张三"):
    return ResumeEvaluation(
        candidate_name=name, resume_content="简历", total_score=85.0, user_id=user.id
    )


async def test_interview_plan_no_specific(eval_user, db_session):
    outcome = await skill_dispatcher.dispatch(
        "interview_plan", _params("生成面试方案"), eval_user, db_session
    )
    assert outcome.artifacts[0]["type"] == "interview_plan_request"
    assert outcome.artifacts[0]["state"] == "no_specific"


async def test_interview_plan_no_match(eval_user, db_session):
    db_session.add(_seed_eval(db_session, eval_user, "张三"))
    await db_session.flush()
    outcome = await skill_dispatcher.dispatch(
        "interview_plan", _params("为李四生成面试方案"), eval_user, db_session
    )
    assert outcome.artifacts[0]["type"] == "interview_plan_request"
    assert outcome.artifacts[0]["state"] == "no_match"


async def test_interview_plan_ambiguous(eval_user, db_session):
    db_session.add(_seed_eval(db_session, eval_user, "张三"))
    db_session.add(_seed_eval(db_session, eval_user, "张三丰"))
    await db_session.flush()
    outcome = await skill_dispatcher.dispatch(
        "interview_plan", _params("为张生成面试方案"), eval_user, db_session
    )
    assert outcome.artifacts[0]["type"] == "interview_plan_request"
    assert outcome.artifacts[0]["state"] == "ambiguous"


async def test_interview_plan_matched(eval_user, db_session):
    jd = await _seed_jd(db_session)
    ev = _seed_eval(db_session, eval_user, "张三")
    ev.job_description_id = jd.id
    db_session.add(ev)
    await db_session.flush()
    outcome = await skill_dispatcher.dispatch(
        "interview_plan", _params("为张三生成面试方案"), eval_user, db_session
    )
    assert outcome.artifacts[0]["type"] == "interview_plan_execute"
    assert outcome.artifacts[0]["candidate_name"] == "张三"


# ---------- resource_delete（两步确认） ----------


async def test_delete_request_returns_candidates(eval_user, db_session):
    jd = await _seed_jd(db_session)
    outcome = await skill_dispatcher.dispatch(
        "resource_delete", _params("删除前端工程师的 JD"), eval_user, db_session
    )
    assert outcome.requires_confirmation is True
    assert outcome.executed is False
    assert outcome.artifacts[0]["type"] == "delete_resource_candidates"
    assert any(c["id"] == str(jd.id) for c in outcome.artifacts[0]["candidates"])
    # 未确认不删除
    from app.services import job_description_service
    assert any(j.id == jd.id for j in await job_description_service.list_jds(db_session))


async def test_delete_confirm_executes(eval_user, db_session):
    jd = await _seed_jd(db_session)
    outcome = await skill_dispatcher.dispatch(
        "resource_delete", _params("确认删除前端工程师的 JD"), eval_user, db_session
    )
    assert outcome.executed is True
    assert outcome.requires_confirmation is False
    assert outcome.artifacts[0]["type"] == "delete_resource_result"
    from app.services import job_description_service
    assert all(j.id != jd.id for j in await job_description_service.list_jds(db_session))
