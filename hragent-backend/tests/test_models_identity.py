"""身份模型单元测试：User 唯一约束 + UserRole 枚举 + Role 多对多。"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Role, User, UserRole


def test_user_role_enum_has_four_members():
    assert {m.value for m in UserRole} == {
        "admin",
        "hr_manager",
        "hr_specialist",
        "employee",
    }


def test_user_role_rejects_invalid_value():
    with pytest.raises(ValueError):
        UserRole("培训管理员")  # 本期不落地的角色


def _make_user(username: str, email: str) -> User:
    return User(
        username=username,
        email=email,
        hashed_password="hashed",
        role=UserRole.employee.value,
    )


async def test_user_unique_username(db_session):
    db_session.add(_make_user("dup", "a@example.com"))
    await db_session.flush()
    db_session.add(_make_user("dup", "b@example.com"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_user_unique_email(db_session):
    db_session.add(_make_user("user1", "same@example.com"))
    await db_session.flush()
    db_session.add(_make_user("user2", "same@example.com"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_user_default_role_is_employee(db_session):
    user = User(username="nobody", email="nobody@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    assert user.role == UserRole.employee.value


async def test_user_role_many_to_many(db_session):
    user = _make_user("hr", "hr@example.com")
    role = Role(name="培训管理员", is_builtin=False)
    # 在对象进入 session 前建立关联（transient 阶段 append 不触发惰性加载）
    user.roles.append(role)
    db_session.add_all([user, role])
    await db_session.flush()

    assert role in user.roles
    assert user in role.users
