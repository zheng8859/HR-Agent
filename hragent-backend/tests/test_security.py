"""认证层单元测试：bcrypt 哈希 + JWT 签发/校验。"""
from datetime import timedelta

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_and_verify():
    hashed = get_password_hash("test-password-123")
    assert hashed != "test-password-123"
    assert verify_password("test-password-123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_hash_is_salted():
    h1 = get_password_hash("same-password")
    h2 = get_password_hash("same-password")
    assert h1 != h2  # 随机盐导致每次不同


def test_jwt_roundtrip():
    token = create_access_token(subject="alice")
    payload = decode_access_token(token)
    assert payload["sub"] == "alice"


def test_jwt_expired():
    token = create_access_token(subject="alice", expires_delta=timedelta(seconds=-10))
    with pytest.raises(JWTError):
        decode_access_token(token)


def test_jwt_tampered():
    token = create_access_token(subject="alice")
    # 篡改最后一个字符
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    with pytest.raises(JWTError):
        decode_access_token(tampered)
