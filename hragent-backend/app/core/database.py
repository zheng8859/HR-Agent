"""异步数据库引擎与会话管理。

pgvector 列类型走 SQLAlchemy 集成（pgvector.sqlalchemy.Vector，自带 bind/result processor），
无需 register_vector —— register_vector 是原生 asyncpg 的编解码器，会与 SQLAlchemy 类型冲突。
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    # 容器内 Postgres 未启用 SSL；禁用避免 asyncpg 在 Windows Proactor 事件循环下的 SSL 协商重置
    connect_args={"ssl": False},
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：yield 一个异步 session，请求结束后关闭。"""
    async with async_session_factory() as session:
        yield session
