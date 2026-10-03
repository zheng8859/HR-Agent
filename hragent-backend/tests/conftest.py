"""pytest 夹具：异步 PostgreSQL 测试库。

Document.embedding 为 pgvector Vector(1536)，故测试库必须用 PostgreSQL（不能用 SQLite）。
会话级：建库 + 建扩展 + 建表一次；函数级：每个测试一个事务，结束回滚实现隔离。
"""
import asyncpg
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base

TEST_DB_NAME = "hragent_test"
TEST_DATABASE_URL = (
    "postgresql+asyncpg://hragent:hragent_dev_password@localhost:5432/hragent_test"
)


async def _ensure_test_db() -> None:
    """连到维护库 hragent 创建 hragent_test（CREATE DATABASE 不能在事务内，故用原生 asyncpg）。"""
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="hragent",
        password="hragent_dev_password",
        database="hragent",
        ssl=False,
    )
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
    )
    if not exists:
        await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    await conn.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    await _ensure_test_db()
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, connect_args={"ssl": False})
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.begin()
        yield session
        await session.rollback()
        await session.close()
