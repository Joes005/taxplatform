import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.audit_workflow_enums import AuditChecklistCategory, AuditChecklistItemStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    pass


class AuditChecklist(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One checklist per engagement — a lightweight container so overall
    progress can be read without scanning every item's engagement_id.
    Items are generated from a documented, hardcoded sample template
    (`app/services/audit_checklist_templates.py`, PHASE7 §13) rather than
    a database-backed template system — the same "small, documented
    sample configuration" precedent Phase 5 set for TDS sections/rates.
    """

    __tablename__ = "audit_checklists"
    __table_args__ = (Index("ix_audit_checklists_engagement_unique", "engagement_id", unique=True),)

    engagement_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_engagements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), default="Standard Review Checklist", nullable=False)

    items: Mapped[list["AuditChecklistItem"]] = relationship(
        "AuditChecklistItem", back_populates="checklist", cascade="all, delete-orphan"
    )


class AuditChecklistItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_checklist_items"
    __table_args__ = (
        Index("ix_audit_checklist_items_engagement_status", "engagement_id", "status"),
    )

    checklist_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_checklists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engagement_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_engagements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[AuditChecklistCategory] = mapped_column(
        Enum(AuditChecklistCategory, native_enum=False, length=20), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[AuditChecklistItemStatus] = mapped_column(
        Enum(AuditChecklistItemStatus, native_enum=False, length=20),
        default=AuditChecklistItemStatus.NOT_STARTED,
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    checklist: Mapped["AuditChecklist"] = relationship("AuditChecklist", back_populates="items")
