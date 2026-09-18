import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.audit_workflow_enums import AuditReviewStatus, AuditReviewType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class AuditReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One review pass over an engagement (PHASE7 §25) — an engagement can
    have several over its life (initial, final, a second reviewer's
    quality check, ...), each preserved rather than overwritten."""

    __tablename__ = "audit_reviews"
    __table_args__ = (Index("ix_audit_reviews_engagement", "engagement_id"),)

    engagement_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_engagements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    review_type: Mapped[AuditReviewType] = mapped_column(
        Enum(AuditReviewType, native_enum=False, length=20), nullable=False
    )
    status: Mapped[AuditReviewStatus] = mapped_column(
        Enum(AuditReviewStatus, native_enum=False, length=15),
        default=AuditReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
