"""AgentServiceCore 单元测试（doc 43 §四/§五/§六）：注册表、缺口、删除解析、记忆、指代、角色。"""
from types import SimpleNamespace

import pytest

from app.services._agent_service_core import (
    MEMORY_MAX_CHARS,
    TOOL_SPECS,
    agent_core,
)

pytestmark = pytest.mark.l1


def _msg(content, context=None):
    return SimpleNamespace(content=content, context=context)


# ---------- 工具注册表 ----------


def test_build_tool_registry_six_tools():
    reg = agent_core._build_tool_registry()
    assert set(reg) == set(TOOL_SPECS)
    assert len(reg) == 6


# ---------- 缺口分类 ----------


def test_missing_required_fields_jd():
    assert agent_core._missing_required_fields("jd", "") == ["job_title"]
    assert agent_core._missing_required_fields("jd", "前端工程师") == []
    assert agent_core._missing_required_fields("chat") == []


# ---------- 删除解析 ----------


def test_fallback_parse_delete_request():
    assert agent_core._fallback_parse_delete_request("删除这份 JD")["resource_type"] == "jd"
    assert agent_core._fallback_parse_delete_request("删掉这个候选人")["resource_type"] == "resume"
    assert agent_core._fallback_parse_delete_request("你好") is None


def test_parse_delete_request_mock_returns_none():
    assert agent_core._parse_delete_request("删除 JD") is None


# ---------- 会话记忆 ----------


def test_build_conversation_memory_within_budget():
    msgs = [_msg("第一句"), _msg("第二句"), _msg("第三句")]
    assert agent_core._build_conversation_memory(msgs) == "第一句\n第二句\n第三句"


def test_build_conversation_memory_truncates_chars():
    long = "长" * 3000
    msgs = [_msg(long), _msg(long), _msg(long)]
    mem = agent_core._build_conversation_memory(msgs)
    assert len(mem) <= MEMORY_MAX_CHARS


def test_build_conversation_memory_limits_messages():
    msgs = [_msg(f"消息{i}") for i in range(20)]
    mem = agent_core._build_conversation_memory(msgs)
    assert "消息0" not in mem
    assert "消息19" in mem


# ---------- 指代解析 ----------


def test_recent_generated_resources():
    ctx = {"agent_response": {"artifacts": [{"type": "job_description", "id": "jd1"}]}}
    msgs = [_msg("帮我生成 JD"), _msg("已生成", context=ctx)]
    found = agent_core._recent_generated_resources(msgs, "job_description")
    assert len(found) == 1
    assert found[0]["id"] == "jd1"


def test_recent_generated_resources_empty():
    msgs = [_msg("你好", context=None)]
    assert agent_core._recent_generated_resources(msgs) == []


# ---------- 角色 gating ----------


@pytest.mark.parametrize(
    "intent,role,expected",
    [
        ("chat", "employee", True),
        ("jd", "employee", False),
        ("jd", "hr_manager", True),
        ("jd", "hr_specialist", True),
        ("resource_delete", "admin", True),
    ],
)
def test_check_role(intent, role, expected):
    assert agent_core.check_role(intent, role) is expected
