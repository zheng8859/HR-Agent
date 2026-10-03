"""FastAPI 依赖注入：认证 → 权限 → 业务。

权限真门在后端（见 CLAUDE.md 六.2）：前端隐藏只是体验优化，接口必须再次校验。
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="无法校验凭据",
    headers={"WWW-Authenticate": "Bearer"},
)

# HR 相关管理接口的角色（权限矩阵：admin / hr_manager / hr_specialist 可管理，employee 不可）
_HR_ADMIN_ROLES = {
    UserRole.admin.value,
    UserRole.hr_manager.value,
    UserRole.hr_specialist.value,
}


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = decode_access_token(token)
        username: str | None = payload.get("sub")
        if username is None:
            raise _CREDENTIALS_EXC
    except JWTError:
        raise _CREDENTIALS_EXC

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise _CREDENTIALS_EXC
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已停用")
    return user


async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    return current_user


async def get_current_admin_by_role(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in _HR_ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    return current_user
