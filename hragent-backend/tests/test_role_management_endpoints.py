"""角色管理端点测试：内置角色预置、自定义角色 CRUD、内置删除保护。"""
from app.core.security import create_access_token, get_password_hash
from app.models import User


def _headers(username):
    return {"Authorization": f"Bearer {create_access_token(subject=username)}"}


async def _make_admin(db_session, username="admin1"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("password123"),
        role="admin",
        is_superuser=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_roles_list_seeds_builtin(client, db_session):
    await _make_admin(db_session)
    h = _headers("admin1")
    resp = await client.get("/api/v1/roles", headers=h)
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert {"admin", "hr_manager", "hr_specialist", "employee"} <= names
    admin_role = next(r for r in resp.json() if r["name"] == "admin")
    assert admin_role["is_builtin"] is True


async def test_create_and_delete_custom_role(client, db_session):
    await _make_admin(db_session)
    h = _headers("admin1")
    resp = await client.post(
        "/api/v1/roles", json={"name": "培训管理员", "description": "培训模块"}, headers=h
    )
    assert resp.status_code == 201
    rid = resp.json()["id"]
    assert resp.json()["is_builtin"] is False

    resp = await client.delete(f"/api/v1/roles/{rid}", headers=h)
    assert resp.status_code == 204


async def test_delete_builtin_role_forbidden(client, db_session):
    await _make_admin(db_session)
    h = _headers("admin1")
    resp = await client.get("/api/v1/roles", headers=h)
    admin_role = next(r for r in resp.json() if r["name"] == "admin")
    resp = await client.delete(f"/api/v1/roles/{admin_role['id']}", headers=h)
    assert resp.status_code == 409
