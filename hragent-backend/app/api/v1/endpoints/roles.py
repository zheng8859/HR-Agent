"""角色管理端点（doc 41）：仅超管（get_current_superuser）。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_superuser
from app.models import User
from app.schemas.user_management import RoleCreate, RoleRead, RoleUpdate
from app.services import role_service

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleRead])
async def list_roles(
    _user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> list[RoleRead]:
    return await role_service.list_roles(db)


@router.post("", response_model=RoleRead, status_code=201)
async def create_role(
    request: RoleCreate,
    _user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    return await role_service.create_role(request, db)


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: uuid.UUID,
    _user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    return await role_service.get_role(role_id, db)


@router.put("/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: uuid.UUID,
    request: RoleUpdate,
    _user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    return await role_service.update_role(role_id, request, db)


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: uuid.UUID,
    _user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> None:
    await role_service.delete_role(role_id, db)
