"""Agent 编排层测试（doc 43 §七 + doc 44 §三）：8 契约字段、缺口、高风险、角色 gating、工具产物、持久化。"""
import logging
from types import SimpleNamespace

import pytest

from app.evaluations.eval_utils import AGENT_CONTRACT_FIELDS
from app.schemas.agent import AgentChatRequest
from app.services import conversation_service
from app.services import agent_service
from app.services.agent_service import _orchestrate, handle_message


def _user(role="hr_manager"):
    return SimpleNamespace(id="00000000-0000-0000-0000-000000000001", username="hr", role=role)


async def test_orchestrate_contract_fields_complete(db_session):
    r = await _orchestrate("生成前端工程师 JD", [], _user(), "", db_session)
    present = set(r.keys())
    assert all(f in present for f in AGENT_CONTRACT_FIELDS)


async def test_orchestrate_jd_missing_title_ask_user(db_session):
    r = await _orchestrate("帮我生成一份 JD", [], _user(), "", db_session)
    assert r["intent"] == "jd"
    assert r["missing_fields"] == ["job_title"]
    assert r["requires_confirmation"] is False
    assert r["artifacts"][0]["type"] == "requirements"


async def test_orchestrate_jd_complete_produces_jd_confirm(db_session):
    r = await _orchestrate("生成前端工程师 JD", [], _user(), "", db_session)
    assert r["intent"] == "jd"
    assert r["missing_fields"] == []
    assert r["artifacts"][0]["type"] == "jd_confirm"


async def test_orchestrate_delete_requires_confirmation(db_session):
    r = await _orchestrate("删除这份 JD", [], _user(), "", db_session)
    assert r["intent"] == "resource_delete"
    assert r["requires_confirmation"] is True
    assert r["artifacts"][0]["type"] == "delete_resource_candidates"


async def test_orchestrate_delete_confirmation_from_spec(db_session, monkeypatch):
    """高风险确认由 TOOL_SPECS 强制派生：分类器漏填/填 False 也强制 True（铁律 #3）。"""

    class _FakeClassifier:
        def classify(self, message, attachments, memory):
            return {
                "intent": "resource_delete",
                "route": "resource",
                "source": "fast",
                "requires_confirmation": False,  # 模拟慢通道 LLM 漏填
                "missing_fields": [],
                "action": "ask_user",
            }

    monkeypatch.setattr(agent_service, "intent_classifier", _FakeClassifier())
    r = await _orchestrate("删除这份 JD", [], _user(), "", db_session)
    assert r["requires_confirmation"] is True
    assert r["artifacts"][0]["type"] == "delete_resource_candidates"


async def test_orchestrate_employee_gated_to_chat(db_session):
    r = await _orchestrate("生成前端工程师 JD", [], _user("employee"), "", db_session)
    assert r["intent"] == "chat"
    assert "权限" in r["message"]


async def test_orchestrate_out_of_scope_replies_cannot(db_session):
    r = await _orchestrate("帮我查社保", [], _user(), "", db_session)
    assert r["intent"] == "chat"
    assert "办不了" in r["message"]


async def test_handle_message_persists_user_and_assistant(db_session, eval_user):
    resp = await handle_message(
        AgentChatRequest(message="生成前端工程师 JD"), eval_user, db_session
    )
    assert resp.conversation_id is not None
    msgs = await conversation_service.list_messages(eval_user, resp.conversation_id, db_session)
    assert len(msgs) == 2
    roles = [m.role for m in msgs]
    assert roles == ["user", "assistant"]
    # assistant 消息 context 落库 agent_response（供指代解析）
    assert msgs[1].context["agent_response"]["intent"] == "jd"


async def test_handle_message_audit_tool_call(db_session, eval_user, caplog):
    with caplog.at_level(logging.INFO, logger="hragent.audit"):
        await handle_message(
            AgentChatRequest(message="生成前端工程师 JD"), eval_user, db_session
        )
    assert any("tool_call" in r.message for r in caplog.records)


async def test_handle_message_audit_high_risk(db_session, eval_user, caplog):
    with caplog.at_level(logging.INFO, logger="hragent.audit"):
        await handle_message(
            AgentChatRequest(message="删除这份 JD"), eval_user, db_session
        )
    assert any("high_risk" in r.message for r in caplog.records)
