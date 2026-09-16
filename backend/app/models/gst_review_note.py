import uuid

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.gst_enums import GSTReviewNoteStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class GSTReviewNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A CA/auditor's note on any GST entity (a GSTR-1 B2B row, a
    reconciliation result, a whole return period, ...) — `entity_type` +
    `entity_id` is a generic reference rather than a dedicated FK per
    entity type, mirroring `DocumentLink` in Phase 2.
    """

    __tablename__ = "gst_review_notes"
    __table_args__ = (
        Index("ix_gst_review_notes_entity", "entity_type", "entity_id"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    return_period_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("gst_return_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[GSTReviewNoteStatus] = mapped_column(
        Enum(GSTReviewNoteStatus, native_enum=False, length=10),
        default=GSTReviewNoteStatus.OPEN,
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
