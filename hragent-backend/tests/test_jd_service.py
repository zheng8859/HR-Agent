"""JD 生成服务单元测试：双入口、需求解析、必填校验、SSE 事件序列、CRUD、状态机。"""
import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models import JDStatus, JobDescription
from app.schemas.job_description import (
    JDGenerateRequest,
    JobDescriptionCreate,
    JobDescriptionUpdate,
)
from app.services import job_description_service as jd_svc


async def test_parse_requirement_extracts_title_and_preserves_raw():
    parsed = await jd_svc.parse_requirement("招聘前端开发工程师，地点上海，薪资20-35K")
    assert parsed.title == "前端开发工程师"
    assert parsed.requirements == ["招聘前端开发工程师，地点上海，薪资20-35K"]


async def test_generate_jd_form_entry():
    request = JDGenerateRequest(title="后端开发工程师", department="技术部", location="北京")
    result = await jd_svc.generate_jd(request)
    assert result.title == "后端开发工程师"
    assert result.department == "技术部"
    assert result.location == "北京"
    assert result.content  # 生成正文非空


async def test_generate_jd_description_entry():
    request = JDGenerateRequest(description="招一个数据工程师")
    result = await jd_svc.generate_jd(request)
    assert result.title == "数据工程师"
    assert result.content
    # 原始需求保留，不静默丢输入
    assert result.requirements == ["招一个数据工程师"]


def test_generate_jd_requires_title_or_description():
    with pytest.raises(ValidationError):
        JDGenerateRequest()


async def test_generate_jd_stream_event_sequence():
    request = JDGenerateRequest(title="前端开发工程师")
    events = []
    async for ev in jd_svc.generate_jd_stream(request):
        events.append(ev)
    assert events[0]["event"] == "thinking"
    assert events[-1]["event"] == "final"
    deltas = [e for e in events if e["event"] == "delta"]
    assert len(deltas) >= 1
    # final 携带完整结构化初稿
    final_data = events[-1]["data"]
    assert final_data["title"] == "前端开发工程师"
    assert final_data["content"]


async def test_generate_jd_stream_retry_after_interrupt():
    request = JDGenerateRequest(title="前端开发工程师")
    gen = jd_svc.generate_jd_stream(request)
    first = await anext(gen)
    assert first["event"] == "thinking"
    await gen.aclose()  # 中断
    # 重试：新生成器正常工作
    gen2 = jd_svc.generate_jd_stream(request)
    assert (await anext(gen2))["event"] == "thinking"
    await gen2.aclose()


# ---------- CRUD 与状态机 ----------


async def test_jd_crud(db_session):
    from app.models import User

    user = User(
        username="hr_crud", email="hr_crud@example.com", hashed_password="x", role="hr_manager"
    )
    db_session.add(user)
    await db_session.flush()

    created = await jd_svc.create_jd(
        JobDescriptionCreate(title="测试岗位", content="岗位正文"), user, db_session
    )
    assert created.id is not None
    assert created.status == JDStatus.draft.value
    assert created.user_id == user.id

    listed = await jd_svc.list_jds(db_session)
    assert any(jd.id == created.id for jd in listed)

    fetched = await jd_svc.get_jd(created.id, db_session)
    assert fetched.title == "测试岗位"

    updated = await jd_svc.update_jd(
        created.id, JobDescriptionUpdate(title="改后岗位"), db_session
    )
    assert updated.title == "改后岗位"

    await jd_svc.delete_jd(created.id, db_session)
    with pytest.raises(HTTPException) as exc:
        await jd_svc.get_jd(created.id, db_session)
    assert exc.value.status_code == 404


async def test_jd_state_machine(db_session):
    from app.models import User

    user = User(username="hr_sm", email="hr_sm@example.com", hashed_password="x", role="hr_manager")
    db_session.add(user)
    await db_session.flush()
    jd = await jd_svc.create_jd(
        JobDescriptionCreate(title="状态机岗位", content="正文"), user, db_session
    )

    published = await jd_svc.change_status(jd.id, "published", db_session)
    assert published.status == "published"

    archived = await jd_svc.change_status(jd.id, "archived", db_session)
    assert archived.status == "archived"

    with pytest.raises(HTTPException) as exc:
        await jd_svc.change_status(jd.id, "invalid", db_session)
    assert exc.value.status_code == 422


async def test_get_jd_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        await jd_svc.get_jd(uuid.uuid4(), db_session)
    assert exc.value.status_code == 404
