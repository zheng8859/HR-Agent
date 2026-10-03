"""审计留痕单元测试（doc 43 §五）：工具调用与高风险操作结构化记录。"""
import logging

import pytest

from app.core.audit import audit_logger

pytestmark = pytest.mark.l1


def test_log_tool_call_record(caplog):
    with caplog.at_level(logging.INFO, logger="hragent.audit"):
        rec = audit_logger.log_tool_call(
            user_id="u1", username="hr", intent="jd", tool="jd", success=True
        )
    assert rec["event"] == "tool_call"
    assert rec["intent"] == "jd"
    assert rec["tool"] == "jd"
    assert rec["success"] is True


def test_log_high_risk_record(caplog):
    with caplog.at_level(logging.INFO, logger="hragent.audit"):
        rec = audit_logger.log_high_risk(
            user_id="u1",
            username="hr",
            intent="resource_delete",
            target="jd",
            outcome="pending_confirmation",
        )
    assert rec["event"] == "high_risk"
    assert rec["outcome"] == "pending_confirmation"


def test_audit_emits_log_line(caplog):
    with caplog.at_level(logging.INFO, logger="hragent.audit"):
        audit_logger.log_tool_call(
            user_id="u1", username="hr", intent="jd", tool="jd", success=True
        )
    assert any("tool_call" in r.message for r in caplog.records)
