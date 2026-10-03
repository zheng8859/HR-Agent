"""统计看板端点（doc 41）：仅 HR 管理员角色可见（get_current_admin_by_role）。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin_by_role
from app.models import User
from app.schemas.stats import ActivityItem, DashboardResponse, TrendResponse
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    _user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    return await stats_service.dashboard_stats(db)


@router.get("/trend", response_model=TrendResponse)
async def trend(
    days: int = Query(30, ge=1, le=90),
    _user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> TrendResponse:
    return await stats_service.trend_data(db, days=days)


@router.get("/activities", response_model=list[ActivityItem])
async def activities(
    limit: int = Query(10, ge=1, le=50),
    _user: User = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityItem]:
    return await stats_service.recent_activities(db, limit=limit)
