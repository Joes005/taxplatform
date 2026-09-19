import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.compliance_enums import NotificationSeverity, NotificationType
from app.models.mixins import UUIDPrimaryKeyMixin
from app.utils.types import GUID


class Notification(UUIDPrimaryKeyMixin, Base):
    """An in-app notification for one user (PHASE9 §18) — no email/SMS/
    push provider exists in this codebase; every notification is created
    and read entirely within this platform. `entity_type`/`entity_id` is
    a generic reference (almost always a `ComplianceTask`, but kept
    generic so a future module can raise notifications without a new
    table) — the same shape used throughout the app for cross-module
    references, e.g. `AuditFinding.source_type`/`source_id`.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_company_user", "company_id", "user_id"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=25), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity, native_enum=False, length=10), default=NotificationSeverity.INFO, nullable=False
    )
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
