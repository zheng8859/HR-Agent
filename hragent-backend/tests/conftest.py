"""pytest 夹具：异步 PostgreSQL 测试库。

Document.embedding 为 pgvector Vector(1536)，故测试库必须用 PostgreSQL（不能用 SQLite）。
会话级：建库 + 建扩展 + 建表一次；函数级：每个测试一个事务，结束回滚实现隔离。
"""
import asyncpg
import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.evaluations.eval_seed import seed_eval_kb
from app.models import Base, User

# 单元/集成测试一律走确定性 mock，不依赖外部 AI 服务（.env 可能已配置真实 key，
# 若不清空会走到真实 API 或 NotImplementedError，导致测试偶发失败/外呼）。
settings.llm_base_url = ""
settings.llm_api_key = ""
settings.embedding_base_url = ""
settings.embedding_api_key = ""
settings.rerank_base_url = ""
settings.rerank_api_key = ""

TEST_DB_NAME = "hragent_test"
# Windows 上 localhost 会优先解析为 IPv6 ::1，asyncpg 直连会超时；显式用 127.0.0.1
TEST_DATABASE_URL = (
    "postgresql+asyncpg://hragent:hragent_dev_password@127.0.0.1:5432/hragent_test"
)

# Golden 测试集根目录（doc 42 §6.1：backend/evals/{agent,dify,rag}_cases/*.json）
EVALS_DIR = Path(__file__).resolve().parent.parent / "evals"


async def _ensure_test_db() -> None:
    """连到维护库 hragent 创建 hragent_test（CREATE DATABASE 不能在事务内，故用原生 asyncpg）。"""
    conn = await asyncpg.connect(
        host="127.0.0.1",
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


@pytest_asyncio.fixture
async def client(db_session):
    """httpx ASGI 客户端：get_db 依赖覆盖到测试事务，便于端点级测试。"""
    import httpx

    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def evals_dir() -> Path:
    """Golden 测试集根目录（供 L1/L3 测试加载样本）。"""
    return EVALS_DIR


@pytest_asyncio.fixture
async def eval_user(db_session) -> User:
    """评测专用用户（hr_manager，可写招聘/知识资源）。"""
    user = User(
        username="eval_user",
        email="eval_user@example.com",
        hashed_password=get_password_hash("secret123"),
        role="hr_manager",
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def eval_kb(db_session, eval_user):
    """评测规范知识库 + 4 篇文档（mock embedding，doc 42 §1.3 检索样本依赖）。"""
    kb = await seed_eval_kb(db_session, eval_user)
    await db_session.flush()
    return kb


@pytest_asyncio.fixture
async def auth_headers(eval_user) -> dict:
    """评测用户的 Bearer 认证头。"""
    token = create_access_token(subject=eval_user.username)
    return {"Authorization": f"Bearer {token}"}
