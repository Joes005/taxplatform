import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.audit_workflow_enums import AuditFindingResponseStatus
from app.models.mixins import UUIDPrimaryKeyMixin
from app.utils.types import GUID


class AuditFindingResponse(UUIDPrimaryKeyMixin, Base):
    """The assignee's formal response to a finding, and the auditor's
    accept/reject decision on it (PHASE7 §24)."""

    __tablename__ = "audit_finding_responses"
    __table_args__ = (Index("ix_audit_finding_responses_finding", "finding_id"),)

    finding_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AuditFindingResponseStatus] = mapped_column(
        Enum(AuditFindingResponseStatus, native_enum=False, length=10),
        default=AuditFindingResponseStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
