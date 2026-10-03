"""对话端点（doc 20 §二 / doc 43）：POST /chat —— 消息发送 / SSE 流式响应（对话入口）。

任意登录用户可对话；工具触发受后端角色 gating（见 agent_service）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.agent import AgentChatRequest
from app.schemas.conversation import FeedbackCreate, FeedbackRead
from app.services import agent_service, conversation_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(
    request: AgentChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        agent_service.stream_chat(request, user, db),
        media_type="text/event-stream",
    )


@router.post("/feedback", response_model=FeedbackRead)
async def feedback(
    payload: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackRead:
    msg = await conversation_service.add_feedback(user, payload.message_id, payload.score, db)
    return FeedbackRead(message_id=msg.id, feedback_score=msg.feedback_score)
