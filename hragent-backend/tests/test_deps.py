"""权限依赖注入单元测试：get_current_user / superuser / admin_by_role。"""
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.deps import get_current_admin_by_role, get_current_superuser, get_current_user
from app.core.security import create_access_token
from app.models import User, UserRole


def _user(**kwargs) -> User:
    defaults = dict(
        username="u",
        email="u@example.com",
        hashed_password="x",
        role=UserRole.employee.value,
        is_superuser=False,
        is_active=True,
    )
    defaults.update(kwargs)
    return User(**defaults)


async def test_get_current_user_valid_token(db_session):
    db_session.add(_user(username="alice", email="alice@example.com"))
    await db_session.flush()

    token = create_access_token(subject="alice")
    user = await get_current_user(token=token, db=db_session)
    assert user.username == "alice"


async def test_get_current_user_expired_token(db_session):
    token = create_access_token(subject="alice", expires_delta=timedelta(seconds=-10))
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


async def test_get_current_user_unknown_subject(db_session):
    token = create_access_token(subject="ghost")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


async def test_get_current_user_inactive(db_session):
    db_session.add(_user(username="bob", email="bob@example.com", is_active=False))
    await db_session.flush()

    token = create_access_token(subject="bob")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 400


async def test_superuser_allows_superuser():
    admin = _user(is_superuser=True)
    assert await get_current_superuser(current_user=admin) is admin


async def test_superuser_rejects_non_superuser():
    with pytest.raises(HTTPException) as exc:
        await get_current_superuser(current_user=_user(is_superuser=False))
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", ["admin", "hr_manager", "hr_specialist"])
async def test_admin_by_role_allows_hr_roles(role):
    user = _user(role=role)
    assert await get_current_admin_by_role(current_user=user) is user


async def test_admin_by_role_rejects_employee():
    with pytest.raises(HTTPException) as exc:
        await get_current_admin_by_role(current_user=_user(role="employee"))
    assert exc.value.status_code == 403
