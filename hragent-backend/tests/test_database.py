"""get_db 依赖测试：请求成功提交、异常回滚，保证跨请求持久化可见。"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import database
from app.models import User


async def test_get_db_commits_on_success(engine, monkeypatch):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session_factory", factory)

    uid = None
    async for session in database.get_db():
        user = User(
            username="persist_me",
            email="persist@example.com",
            hashed_password="x",
            role="employee",
        )
        session.add(user)
        await session.flush()
        uid = user.id
    # 循环自然结束 → get_db 在 yield 后执行 commit

    async with factory() as fresh:
        row = (
            await fresh.execute(select(User).where(User.id == uid))
        ).scalar_one_or_none()
        assert row is not None  # 新 session 可见 → 已提交


async def test_get_db_rolls_back_on_error(engine, monkeypatch):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session_factory", factory)

    with pytest.raises(RuntimeError):
        async for session in database.get_db():
            session.add(
                User(
                    username="rollback_me",
                    email="rollback@example.com",
                    hashed_password="x",
                    role="employee",
                )
            )
            await session.flush()
            raise RuntimeError("boom")

    async with factory() as fresh:
        row = (
            await fresh.execute(select(User).where(User.username == "rollback_me"))
        ).scalar_one_or_none()
        assert row is None  # 异常已回滚，不残留
