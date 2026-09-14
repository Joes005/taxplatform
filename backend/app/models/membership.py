from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.role import Role
    from app.models.user import User


class MembershipStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    INVITED = "INVITED"


class CompanyMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Links a User to a Company under a specific Role.

    This is the core of the multi-tenant model: a user may hold one
    membership per company, and their effective permissions for that tenant
    are derived entirely from the membership's role.
    """

    __tablename__ = "company_memberships"
    __table_args__ = (
        Index(
            "ix_membership_unique_active_user_company",
            "user_id",
            "company_id",
            unique=True,
            postgresql_where="status = 'ACTIVE'",
            sqlite_where="status = 'ACTIVE'",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )

    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, native_enum=False, length=20),
        default=MembershipStatus.ACTIVE,
        nullable=False,
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="memberships")
    company: Mapped["Company"] = relationship("Company", back_populates="memberships")
    role: Mapped["Role"] = relationship("Role", back_populates="memberships")
