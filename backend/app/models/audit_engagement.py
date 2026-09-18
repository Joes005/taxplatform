import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.audit_workflow_enums import AuditEngagementStatus, AuditEngagementType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.audit_assignment import AuditAssignment


class AuditEngagement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A CA/Auditor review workspace over one company's financial/
    compliance data for one period — a workflow and traceability tool,
    never a statutory certification (PHASE7 §2, §29). `is_locked` is a
    separate immutability switch reachable only once `status=CLOSED`; it
    is not itself a lifecycle state.
    """

    __tablename__ = "audit_engagements"
    __table_args__ = (
        Index("ix_audit_engagements_company_code", "company_id", "engagement_code", unique=True),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engagement_code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    engagement_type: Mapped[AuditEngagementType] = mapped_column(
        Enum(AuditEngagementType, native_enum=False, length=25),
        default=AuditEngagementType.INTERNAL_REVIEW,
        nullable=False,
    )
    status: Mapped[AuditEngagementStatus] = mapped_column(
        Enum(AuditEngagementStatus, native_enum=False, length=25),
        default=AuditEngagementStatus.DRAFT,
        nullable=False,
        index=True,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    assignments: Mapped[list["AuditAssignment"]] = relationship(
        "AuditAssignment", back_populates="engagement", cascade="all, delete-orphan"
    )
