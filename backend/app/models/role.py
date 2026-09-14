from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.membership import CompanyMembership
    from app.models.permission import RolePermission


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # System roles (SUPER_ADMIN, COMPANY_ADMIN, ACCOUNTANT, AUDITOR) are seeded
    # and cannot be deleted or renamed through the API.
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permission_links: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["CompanyMembership"]] = relationship(
        "CompanyMembership", back_populates="role"
    )
