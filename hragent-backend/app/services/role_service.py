"""角色管理服务：内置角色预置、自定义角色 CRUD、内置保护（doc 41 §角色管理）。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Role
from app.schemas.user_management import RoleCreate, RoleUpdate

BUILTIN_ROLES = [
    ("admin", "超级管理员"),
    ("hr_manager", "HR 负责人"),
    ("hr_specialist", "HR 专员"),
    ("employee", "普通员工"),
]


async def ensure_builtin_roles(db: AsyncSession) -> None:
    """幂等预置 4 个内置角色（应用启动时 + 列表/详情时兜底）。"""
    existing = set((await db.execute(select(Role.name))).scalars().all())
    for name, description in BUILTIN_ROLES:
        if name not in existing:
            db.add(Role(name=name, description=description, is_builtin=True))
    await db.flush()


async def _ensure_name_unique(
    name: str, db: AsyncSession, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = select(Role).where(Role.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Role.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="角色名称已存在")


async def list_roles(db: AsyncSession) -> list[Role]:
    await ensure_builtin_roles(db)
    result = await db.execute(select(Role).order_by(Role.created_at.asc()))
    return list(result.scalars().all())


async def get_role(role_id: uuid.UUID, db: AsyncSession) -> Role:
    await ensure_builtin_roles(db)
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return role


async def create_role(request: RoleCreate, db: AsyncSession) -> Role:
    await _ensure_name_unique(request.name, db)
    role = Role(name=request.name, description=request.description, is_builtin=False)
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


async def update_role(role_id: uuid.UUID, request: RoleUpdate, db: AsyncSession) -> Role:
    role = await get_role(role_id, db)
    if request.name is not None and request.name != role.name:
        if role.is_builtin:
            raise HTTPException(status_code=409, detail="内置角色不可重命名")
        await _ensure_name_unique(request.name, db, exclude_id=role.id)
        role.name = request.name
    if request.description is not None:
        role.description = request.description
    await db.flush()
    await db.refresh(role)
    return role


async def delete_role(role_id: uuid.UUID, db: AsyncSession) -> None:
    role = await get_role(role_id, db)
    if role.is_builtin:
        raise HTTPException(status_code=409, detail="内置角色不可删除")
    await db.delete(role)
    await db.flush()
