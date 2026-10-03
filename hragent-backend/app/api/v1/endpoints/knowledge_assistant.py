"""知识问答端点（doc 40）：POST /knowledge-assistant/ask。

读操作走 `get_current_user`（任意登录用户），检索范围按用户隔离（见 rag_service）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.knowledge_assistant import KnowledgeAskRequest, KnowledgeAskResponse
from app.services import rag_service

router = APIRouter(prefix="/knowledge-assistant", tags=["knowledge-assistant"])


@router.post("/ask", response_model=KnowledgeAskResponse)
async def ask(
    payload: KnowledgeAskRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeAskResponse:
    return await rag_service.ask(payload.question, user, payload.knowledge_base_id, db)
