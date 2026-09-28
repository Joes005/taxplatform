import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin
from app.utils.types import GUID


class ComplianceObligationEvidence(UUIDPrimaryKeyMixin, Base):
    """Links a compliance obligation directly to an existing Phase 2 `Document`
    (PHASE13 §12) — reuses existing file storage, tenant-isolated.
    """

    __tablename__ = "compliance_obligation_evidence"
    __table_args__ = (
        Index("ix_compliance_obligation_evidence_obligation", "obligation_id"),
        Index("ix_compliance_obligation_evidence_company", "company_id"),
    )

    obligation_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("compliance_obligations.id", ondelete="CASCADE"), nullable=False, index=True
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
