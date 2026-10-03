"""用户管理服务：CRUD、用户名/邮箱唯一、密码哈希、响应不回传（doc 41 §用户管理）。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models import User
from app.schemas.user_management import UserCreate, UserUpdate


async def _ensure_username_unique(
    username: str, db: AsyncSession, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = select(User).where(User.username == username)
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")


async def _ensure_email_unique(
    email: str, db: AsyncSession, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = select(User).where(User.email == email)
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="邮箱已存在")


async def create_user(request: UserCreate, db: AsyncSession) -> User:
    await _ensure_username_unique(request.username, db)
    await _ensure_email_unique(request.email, db)
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        phone=request.phone,
        department=request.department,
        position=request.position,
        employee_id=request.employee_id,
        role=request.role.value,
        is_active=request.is_active,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


async def get_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


async def update_user(user_id: uuid.UUID, request: UserUpdate, db: AsyncSession) -> User:
    user = await get_user(user_id, db)
    if request.username is not None and request.username != user.username:
        await _ensure_username_unique(request.username, db, exclude_id=user.id)
        user.username = request.username
    if request.email is not None and request.email != user.email:
        await _ensure_email_unique(request.email, db, exclude_id=user.id)
        user.email = request.email
    if request.password is not None:
        user.hashed_password = get_password_hash(request.password)
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.phone is not None:
        user.phone = request.phone
    if request.department is not None:
        user.department = request.department
    if request.position is not None:
        user.position = request.position
    if request.employee_id is not None:
        user.employee_id = request.employee_id
    if request.role is not None:
        user.role = request.role.value
    if request.is_active is not None:
        user.is_active = request.is_active
    if request.is_superuser is not None:
        user.is_superuser = request.is_superuser
    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(user_id: uuid.UUID, db: AsyncSession) -> None:
    user = await get_user(user_id, db)
    await db.delete(user)
    await db.flush()
