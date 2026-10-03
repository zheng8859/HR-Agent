"""密码哈希与 JWT 签发/校验。

密码用 bcrypt 直接调用（passlib 1.7.4 与 bcrypt 5.0 不兼容，见 design.md R1）。
bcrypt 对 >72 字节密码抛 ValueError，由 schema 层 max_length 约束。
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = settings.jwt_algorithm


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解码并校验 JWT；失败抛 JWTError。"""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
