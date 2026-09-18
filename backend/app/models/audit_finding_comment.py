import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin
from app.utils.types import GUID


class AuditFindingComment(UUIDPrimaryKeyMixin, Base):
    """Append-only discussion on a finding (PHASE7 §23) — no update/delete
    endpoint is exposed, so the timeline can never be silently rewritten.
    """

    __tablename__ = "audit_finding_comments"
    __table_args__ = (Index("ix_audit_finding_comments_finding", "finding_id"),)

    finding_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
