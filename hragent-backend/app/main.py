"""HR Agent 后端入口（FastAPI）。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.database import async_session_factory
from app.services import role_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时幂等预置内置角色（测试中由 role_service 列表/详情兜底）。"""
    async with async_session_factory() as db:
        await role_service.ensure_builtin_roles(db)
        await db.commit()
    yield


app = FastAPI(title="HR Agent API", version="0.5.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    """健康检查，免认证（见 20-API设计）。"""
    return {"status": "ok"}
