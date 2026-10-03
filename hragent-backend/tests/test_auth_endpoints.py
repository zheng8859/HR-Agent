"""认证端点测试：登录签发 JWT、当前用户。"""
from app.core.security import get_password_hash
from app.models import User


async def _make_user(db_session, username="hr", password="secret123", **kwargs):
    defaults = dict(
        email=f"{username}@example.com",
        hashed_password=get_password_hash(password),
        role="hr_manager",
        is_superuser=False,
        is_active=True,
    )
    defaults.update(kwargs)
    user = User(username=username, **defaults)
    db_session.add(user)
    await db_session.flush()
    return user


async def test_login_success(client, db_session):
    await _make_user(db_session)
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "hr", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_login_wrong_password(client, db_session):
    await _make_user(db_session)
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "hr", "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client, db_session):
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "ghost", "password": "x"},
    )
    assert resp.status_code == 401


async def test_me_with_token(client, db_session):
    user = await _make_user(db_session)
    from app.core.security import create_access_token

    token = create_access_token(subject=user.username)
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "hr"


async def test_me_without_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
