"""审计留痕（doc 25 §2.1 口径 / doc 43）：工具调用与高风险操作结构化日志 + 可查询记录。

本期 10 张本地表不含审计表，故留痕落在两处：结构化日志（`hragent.audit` logger）+
Message.context JSONB（工具调用写进 assistant 消息上下文，可查、可复用）。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

_audit_logger = logging.getLogger("hragent.audit")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditLogger:
    """审计记录器：返回结构化记录（可断言）+ 写入 logger（可观测）。"""

    def _emit(self, record: dict[str, Any]) -> dict[str, Any]:
        _audit_logger.info(json.dumps(record, ensure_ascii=False))
        return record

    def log_tool_call(
        self,
        *,
        user_id: uuid.UUID | str,
        username: str,
        intent: str,
        tool: str,
        success: bool,
        detail: str = "",
    ) -> dict[str, Any]:
        return self._emit(
            {
                "event": "tool_call",
                "ts": _now_iso(),
                "user_id": str(user_id),
                "username": username,
                "intent": intent,
                "tool": tool,
                "success": success,
                "detail": detail,
            }
        )

    def log_high_risk(
        self,
        *,
        user_id: uuid.UUID | str,
        username: str,
        intent: str,
        target: str,
        outcome: str,
        detail: str = "",
    ) -> dict[str, Any]:
        return self._emit(
            {
                "event": "high_risk",
                "ts": _now_iso(),
                "user_id": str(user_id),
                "username": username,
                "intent": intent,
                "target": target,
                "outcome": outcome,
                "detail": detail,
            }
        )


# 服务层共享的默认审计器
audit_logger = AuditLogger()
