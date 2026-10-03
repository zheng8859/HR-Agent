"""用户管理端点测试：CRUD、密码不回传、角色枚举校验、删除自我保护、超管权限。"""
from app.core.security import create_access_token, get_password_hash
from app.models import User


def _headers(username):
    return {"Authorization": f"Bearer {create_access_token(subject=username)}"}


async def _make_user(db_session, username, role="employee", is_superuser=False, is_active=True):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("password123"),
        role=role,
        is_superuser=is_superuser,
        is_active=is_active,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_user_crud_flow(client, db_session):
    admin = await _make_user(db_session, "admin1", role="admin", is_superuser=True)
    h = _headers("admin1")

    # 创建
    resp = await client.post(
        "/api/v1/users",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
            "full_name": "爱丽丝",
            "role": "hr_specialist",
            "department": "招聘组",
        },
        headers=h,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "hr_specialist"
    assert "hashed_password" not in body
    assert "password" not in body
    user_id = body["id"]

    # 列表（不假设表为空：其他测试可能已提交用户）
    resp = await client.get("/api/v1/users", headers=h)
    assert resp.status_code == 200
    usernames = {u["username"] for u in resp.json()["items"]}
    assert {"admin1", "alice"} <= usernames

    # 详情
    resp = await client.get(f"/api/v1/users/{user_id}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"

    # 更新（禁用）
    resp = await client.put(f"/api/v1/users/{user_id}", json={"is_active": False}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # 删除
    resp = await client.delete(f"/api/v1/users/{user_id}", headers=h)
    assert resp.status_code == 204

    # 不能删除自己
    resp = await client.delete(f"/api/v1/users/{admin.id}", headers=h)
    assert resp.status_code == 400


async def test_user_role_enum_validation(client, db_session):
    await _make_user(db_session, "admin1", role="admin", is_superuser=True)
    h = _headers("admin1")
    resp = await client.post(
        "/api/v1/users",
        json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "password123",
            "role": "培训管理员",
        },
        headers=h,
    )
    assert resp.status_code == 422


async def test_non_superuser_forbidden(client, db_session):
    await _make_user(db_session, "hr", role="hr_manager")
    h = _headers("hr")
    resp = await client.get("/api/v1/users", headers=h)
    assert resp.status_code == 403
