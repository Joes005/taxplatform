import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.audit_finding import AuditFinding


class AuditFindingEvidence(UUIDPrimaryKeyMixin, Base):
    """Links a finding to an existing Phase 2 `Document` — never a second
    file-storage system (PHASE7 §21-22). Only `document_id` is a real FK;
    the physical file is never copied, and the document must already
    belong to the same company (validated in `AuditFindingService`, not
    by this model).
    """

    __tablename__ = "audit_finding_evidence"
    __table_args__ = (Index("ix_audit_finding_evidence_finding", "finding_id"),)

    finding_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("audit_findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    added_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    finding: Mapped["AuditFinding"] = relationship("AuditFinding", back_populates="evidence")
