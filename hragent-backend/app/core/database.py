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
    """FastAPI 依赖：yield 一个异步 session，请求成功提交、异常回滚，结束后关闭。

    服务层只做 flush（不 commit），持久化由本依赖在请求结束时统一提交，
    保证跨请求可见（list 能读到刚写入的记录）。
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
