"""评分标准服务单元测试：维度结构、总分默认 100、权重配平、绑定 JD、CRUD。"""
import uuid

import pytest
from fastapi import HTTPException

from app.models import ScoringStatus
from app.schemas.scoring_criteria import (
    ScoringCriteriaCreate,
    ScoringDimension,
    ScoringGenerateRequest,
)
from app.services import scoring_criteria_service as sc_svc


async def test_generate_scoring_dimensions_structure():
    result = await sc_svc.generate_scoring_criteria(
        ScoringGenerateRequest(job_title="前端开发工程师", content="JD 正文")
    )
    assert result.total_score == 100
    assert len(result.dimensions) >= 1
    for dim in result.dimensions:
        assert dim.name
        assert dim.max_score >= 0
        assert dim.weight >= 0


async def test_generate_scoring_total_default_100():
    result = await sc_svc.generate_scoring_criteria(
        ScoringGenerateRequest(job_title="X", content="Y")
    )
    assert result.total_score == 100


def test_validate_balance_balanced():
    dims = [
        ScoringDimension(name="a", weight=40, max_score=40),
        ScoringDimension(name="b", weight=30, max_score=30),
        ScoringDimension(name="c", weight=30, max_score=30),
    ]
    balance = sc_svc.validate_balance(dims, 100)
    assert balance.is_balanced is True
    assert balance.score_sum == 100
    assert balance.difference == 0


def test_validate_balance_unbalanced_not_corrected():
    # 模拟评测抓到的「分值相加 110 分」错误
    dims = [
        ScoringDimension(name="a", weight=50, max_score=50),
        ScoringDimension(name="b", weight=40, max_score=40),
        ScoringDimension(name="c", weight=20, max_score=20),
    ]
    balance = sc_svc.validate_balance(dims, 100)
    assert balance.is_balanced is False
    assert balance.score_sum == 110
    assert balance.difference == -10
    # 不自动改写：原始分值保持不变
    assert [d.max_score for d in dims] == [50, 40, 20]


# ---------- CRUD 与绑定 ----------


async def test_scoring_crud_and_bind_jd(db_session):
    from app.models import JobDescription

    jd = JobDescription(title="绑定岗位", content="正文")
    db_session.add(jd)
    await db_session.flush()

    created = await sc_svc.create_scoring_criteria(
        ScoringCriteriaCreate(
            title="评分标准A",
            content="正文",
            job_description_id=jd.id,
            scoring_dimensions=[
                ScoringDimension(name="a", weight=60, max_score=60),
                ScoringDimension(name="b", weight=40, max_score=40),
            ],
        ),
        db_session,
    )
    assert created.status == ScoringStatus.draft.value
    assert created.job_description_id == jd.id
    assert created.scoring_dimensions[0]["name"] == "a"

    fetched = await sc_svc.get_scoring_criteria(created.id, db_session)
    assert fetched.title == "评分标准A"

    await sc_svc.delete_scoring_criteria(created.id, db_session)
    with pytest.raises(HTTPException) as exc:
        await sc_svc.get_scoring_criteria(created.id, db_session)
    assert exc.value.status_code == 404


async def test_scoring_bind_nonexistent_jd_404(db_session):
    with pytest.raises(HTTPException) as exc:
        await sc_svc.create_scoring_criteria(
            ScoringCriteriaCreate(
                title="X", content="Y", job_description_id=uuid.uuid4()
            ),
            db_session,
        )
    assert exc.value.status_code == 404


async def test_scoring_state_machine(db_session):
    created = await sc_svc.create_scoring_criteria(
        ScoringCriteriaCreate(title="S", content="C"), db_session
    )
    active = await sc_svc.change_status(created.id, "active", db_session)
    assert active.status == "active"

    with pytest.raises(HTTPException) as exc:
        await sc_svc.change_status(created.id, "invalid", db_session)
    assert exc.value.status_code == 422
