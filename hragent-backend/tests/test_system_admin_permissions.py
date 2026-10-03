"""系统管理权限边界测试：统计看板按角色、系统管理仅超管。"""
from app.core.security import create_access_token, get_password_hash
from app.models import User


def _headers(username):
    return {"Authorization": f"Bearer {create_access_token(subject=username)}"}


async def _make_user(db_session, username, role="employee", is_superuser=False):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("password123"),
        role=role,
        is_superuser=is_superuser,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_stats_permission_by_role(client, db_session):
    await _make_user(db_session, "emp", role="employee")
    await _make_user(db_session, "hr", role="hr_manager")
    # 普通员工不可看统计
    resp = await client.get("/api/v1/stats/dashboard", headers=_headers("emp"))
    assert resp.status_code == 403
    # HR 负责人可看统计
    resp = await client.get("/api/v1/stats/dashboard", headers=_headers("hr"))
    assert resp.status_code == 200


async def test_system_management_superuser_only(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    await _make_user(db_session, "admin1", role="admin", is_superuser=True)
    # hr_manager 非超管 → 403
    assert (await client.get("/api/v1/users", headers=_headers("hr"))).status_code == 403
    assert (await client.get("/api/v1/roles", headers=_headers("hr"))).status_code == 403
    # 超管 → 200
    assert (await client.get("/api/v1/users", headers=_headers("admin1"))).status_code == 200
    assert (await client.get("/api/v1/roles", headers=_headers("admin1"))).status_code == 200
