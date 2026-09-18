import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.audit_workflow_enums import (
    AuditFindingCategory,
    AuditFindingSeverity,
    AuditFindingSourceType,
    AuditFindingStatus,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    pass


class AuditFinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One exception/observation raised during an engagement.
    `source_type`/`source_id` is a generic reference (PHASE7 §15) — the
    same shape `TDSTransaction`/`BankTransactionMatch` already use — so a
    finding can point into Accounting, GST, TDS, Bank, or Documents
    without a hard FK into five different tables; ownership is validated
    at write time in `AuditFindingService`, never trusted blindly.
    Severity is an internal workflow classification only, never a legal
    or fraud determination (PHASE7 §18, §55).
    """

    __tablename__ = "audit_findings"
    __table_args__ = (
        Index("ix_audit_findings_engagement_code", "engagement_id", "finding_code", unique=True),
        Index("ix_audit_findings_company_status", "company_id", "status"),
        Index("ix_audit_findings_source", "source_type", "source_id"),
    )

    engagement_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_engagements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finding_code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[AuditFindingCategory] = mapped_column(
        Enum(AuditFindingCategory, native_enum=False, length=20), nullable=False, index=True
    )
    severity: Mapped[AuditFindingSeverity] = mapped_column(
        Enum(AuditFindingSeverity, native_enum=False, length=10), nullable=False, index=True
    )
    status: Mapped[AuditFindingStatus] = mapped_column(
        Enum(AuditFindingStatus, native_enum=False, length=20),
        default=AuditFindingStatus.OPEN,
        nullable=False,
        index=True,
    )

    source_type: Mapped[AuditFindingSourceType | None] = mapped_column(
        Enum(AuditFindingSourceType, native_enum=False, length=20), nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    evidence: Mapped[list["AuditFindingEvidence"]] = relationship(
        "AuditFindingEvidence", back_populates="finding", cascade="all, delete-orphan"
    )
