"""HR Agent 后端入口（FastAPI）。"""
from fastapi import FastAPI

from app.api.v1.api import api_router

app = FastAPI(title="HR Agent API", version="0.2.0")
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    """健康检查，免认证（见 20-API设计）。"""
    return {"status": "ok"}
