"""Agent 任务端点（doc 20 §二 / doc 43）：POST /agent —— 任务发起 / 任务型流式事件。

任务型 SSE：progress → delta → artifact → final（doc 16 §7.3）。工具 handler 为 stub（文档 44）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.agent import AgentChatRequest
from app.services import agent_service

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("")
async def run_agent(
    request: AgentChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        agent_service.stream_agent(request, user, db),
        media_type="text/event-stream",
    )
