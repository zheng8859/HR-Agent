"""意图识别端点（doc 20 §二 / doc 43）：POST /intent —— 快慢双通道入口，非流式。

读操作走 `get_current_user`（任意登录用户）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models import User
from app.schemas.agent import IntentClassifyRequest, IntentClassifyResponse
from app.services.intent_service import intent_classifier

router = APIRouter(prefix="/intent", tags=["intent"])


@router.post("", response_model=IntentClassifyResponse)
async def classify(
    payload: IntentClassifyRequest,
    _: User = Depends(get_current_user),
) -> IntentClassifyResponse:
    result = intent_classifier.classify(payload.message, payload.attachments)
    return IntentClassifyResponse(
        intent=result["intent"],
        route=result["route"],
        tool=result.get("tool") or None,
        action=result["action"],
        requires_confirmation=result["requires_confirmation"],
        missing_fields=result["missing_fields"],
        source=result["source"],
    )
