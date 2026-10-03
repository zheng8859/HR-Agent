"""用户管理端点（doc 41）：仅超管（get_current_superuser）。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_superuser
from app.models import User
from app.schemas.user_management import UserCreate, UserListOut, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListOut)
async def list_users(
    _user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> UserListOut:
    users = await user_service.list_users(db)
    return UserListOut(total=len(users), items=users)


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    request: UserCreate,
    _user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    return await user_service.create_user(request, db)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: uuid.UUID,
    _user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    return await user_service.get_user(user_id, db)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    request: UserUpdate,
    _user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    return await user_service.update_user(user_id, request, db)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> None:
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    await user_service.delete_user(user_id, db)
