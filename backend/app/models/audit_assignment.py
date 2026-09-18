import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.audit_workflow_enums import AuditAssignmentRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.audit_engagement import AuditEngagement


class AuditAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One user's role on one engagement. `user_id` must hold an active
    `CompanyMembership` for the engagement's `company_id` at assignment
    time (PHASE7 §10) — this table never creates a new kind of user or
    bypasses existing company membership/RBAC. Unassigning sets
    `is_active=False`/`unassigned_at` rather than deleting the row, so
    "who was on this engagement and when" is never lost.
    """

    __tablename__ = "audit_assignments"
    __table_args__ = (
        Index(
            "ix_audit_assignments_unique_active",
            "engagement_id",
            "user_id",
            "role",
            unique=True,
            postgresql_where="is_active = true",
            sqlite_where="is_active = 1",
        ),
    )

    engagement_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_engagements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    role: Mapped[AuditAssignmentRole] = mapped_column(
        Enum(AuditAssignmentRole, native_enum=False, length=20), nullable=False
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    engagement: Mapped["AuditEngagement"] = relationship("AuditEngagement", back_populates="assignments")
