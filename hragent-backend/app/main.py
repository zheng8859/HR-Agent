"""HR Agent 后端入口（FastAPI）。骨架占位，后续按阶段补齐。"""
from fastapi import FastAPI

app = FastAPI(title="HR Agent API", version="0.1.0")


@app.get("/health", tags=["health"])
async def health() -> dict:
    """健康检查，免认证（见 20-API设计）。"""
    return {"status": "ok"}
