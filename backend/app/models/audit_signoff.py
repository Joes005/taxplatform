import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.audit_workflow_enums import AuditSignOffType
from app.models.mixins import UUIDPrimaryKeyMixin
from app.utils.types import GUID


class AuditSignOff(UUIDPrimaryKeyMixin, Base):
    """An internal application acknowledgement that an engagement's
    review is complete — explicitly not a DSC, ICAI, or government
    signature, and `statement` is always a neutral, non-statutory
    sentence (PHASE7 §28-29; the exact wording is fixed in
    `AuditEngagementService`, never freely authored, so the platform can
    never be made to emit a "legally certified"-style claim).
    """

    __tablename__ = "audit_signoffs"
    __table_args__ = (Index("ix_audit_signoffs_engagement", "engagement_id"),)

    engagement_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_engagements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    signed_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    sign_off_type: Mapped[AuditSignOffType] = mapped_column(
        Enum(AuditSignOffType, native_enum=False, length=25), nullable=False
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
