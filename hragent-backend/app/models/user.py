"""用户实体 + 角色代码枚举。"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    """4 种角色代码枚举（本期口径，见 CLAUDE.md 七）。"""

    admin = "admin"
    hr_manager = "hr_manager"
    hr_specialist = "hr_specialist"
    employee = "employee"


class User(BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 单一主角色（代码枚举值），权限矩阵以它为准
    role: Mapped[str] = mapped_column(
        String(32), default=UserRole.employee.value, nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 动态 Role 表多对多（本期默认角色之外，培训管理员等由动态 Role 承接）
    roles: Mapped[list[Role]] = relationship(
        "Role", secondary="user_role", back_populates="users"
    )
