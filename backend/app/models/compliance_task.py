import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.compliance_enums import (
    ComplianceCategory,
    CompliancePriority,
    ComplianceModule,
    ComplianceSourceType,
    ComplianceTaskStatus,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class ComplianceTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One unit of compliance work (PHASE9 §12) — optionally generated
    from a `ComplianceObligation`, optionally traceable to an existing
    module record via `source_type`/`source_id` (PHASE9 §35, the same
    generic-reference shape `TDSTransaction`/`AuditFinding` already use),
    always company-scoped. Status transitions are enforced entirely by
    `ComplianceTaskService`'s transition table (PHASE9 §43) — never set
    directly by a route handler.
    """

    __tablename__ = "compliance_tasks"
    __table_args__ = (
        Index("ix_compliance_tasks_company_status", "company_id", "status"),
        Index("ix_compliance_tasks_company_due_date", "company_id", "due_date"),
        Index("ix_compliance_tasks_source", "source_type", "source_id"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    obligation_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("compliance_obligations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ComplianceCategory] = mapped_column(
        Enum(ComplianceCategory, native_enum=False, length=15), nullable=False, index=True
    )
    module: Mapped[ComplianceModule] = mapped_column(
        Enum(ComplianceModule, native_enum=False, length=25), nullable=False, index=True
    )
    status: Mapped[ComplianceTaskStatus] = mapped_column(
        Enum(ComplianceTaskStatus, native_enum=False, length=15),
        default=ComplianceTaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority: Mapped[CompliancePriority] = mapped_column(
        Enum(CompliancePriority, native_enum=False, length=10), default=CompliancePriority.MEDIUM, nullable=False, index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_type: Mapped[ComplianceSourceType] = mapped_column(
        Enum(ComplianceSourceType, native_enum=False, length=20), default=ComplianceSourceType.MANUAL, nullable=False
    )
    source_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class ComplianceTaskComment(UUIDPrimaryKeyMixin, Base):
    """Append-only discussion on a task (PHASE9 §14) — mirrors
    `AuditFindingComment`'s own append-only shape; no update/delete route
    is exposed, so the discussion trail can never be silently rewritten.
    """

    __tablename__ = "compliance_task_comments"
    __table_args__ = (Index("ix_compliance_task_comments_task", "task_id"),)

    task_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("compliance_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ComplianceTaskEvidence(UUIDPrimaryKeyMixin, Base):
    """Links a task to an existing Phase 2 `Document` (PHASE9 §15) —
    never a second file-storage system, the same thin-join shape
    `AuditFindingEvidence` already established. Only `document_id` is a
    real FK; the document must already belong to the same company,
    validated in `ComplianceTaskService`, not by this model.
    """

    __tablename__ = "compliance_task_evidence"
    __table_args__ = (Index("ix_compliance_task_evidence_task", "task_id"),)

    task_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("compliance_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
