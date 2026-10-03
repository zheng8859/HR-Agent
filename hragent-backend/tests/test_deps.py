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


# doc 14 功能权限矩阵（本期口径）→ 三依赖函数授权结果。
# admin：全权限；hr_manager / hr_specialist：HR 管理（招聘/统计）但不碰系统管理；
# employee：仅知识问答/普通对话（get_current_user 即可，无角色门禁）。
ROLE_DEP_MATRIX = {
    "admin": {"user": True, "superuser": True, "admin_by_role": True},
    "hr_manager": {"user": True, "superuser": False, "admin_by_role": True},
    "hr_specialist": {"user": True, "superuser": False, "admin_by_role": True},
    "employee": {"user": True, "superuser": False, "admin_by_role": False},
}


def _matrix_user(role: str) -> User:
    # 实践口径：仅 admin 拥有 superuser 标志；其余角色 is_superuser=False。
    return _user(role=role, is_superuser=(role == "admin"))


@pytest.mark.parametrize("role", list(ROLE_DEP_MATRIX))
async def test_matrix_get_current_user(role, db_session):
    username = f"{role}_u"
    db_session.add(
        _user(username=username, email=f"{username}@example.com", role=role)
    )
    await db_session.flush()

    token = create_access_token(subject=username)
    user = await get_current_user(token=token, db=db_session)
    assert user.username == username
    # get_current_user 只做认证，不按角色拒绝——所有启用角色均可进入（知识问答/普通对话）。
    assert ROLE_DEP_MATRIX[role]["user"] is True


@pytest.mark.parametrize("role", list(ROLE_DEP_MATRIX))
async def test_matrix_get_current_superuser(role):
    user = _matrix_user(role)
    allowed = ROLE_DEP_MATRIX[role]["superuser"]
    if allowed:
        assert await get_current_superuser(current_user=user) is user
    else:
        with pytest.raises(HTTPException) as exc:
            await get_current_superuser(current_user=user)
        assert exc.value.status_code == 403


@pytest.mark.parametrize("role", list(ROLE_DEP_MATRIX))
async def test_matrix_get_current_admin_by_role(role):
    user = _matrix_user(role)
    allowed = ROLE_DEP_MATRIX[role]["admin_by_role"]
    if allowed:
        assert await get_current_admin_by_role(current_user=user) is user
    else:
        with pytest.raises(HTTPException) as exc:
            await get_current_admin_by_role(current_user=user)
        assert exc.value.status_code == 403
