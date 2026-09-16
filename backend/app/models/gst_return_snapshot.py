import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.gst_enums import GSTReturnSnapshotStatus, GSTReturnType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class GSTReturnSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A point-in-time, versioned copy of a generated GSTR-1/GSTR-3B
    preparation. Accounting data is mutable; a finalized return preparation
    must not silently drift when a later edit changes an underlying
    invoice, so each generation is preserved here rather than only ever
    being recomputed live (PHASE4 sections 16, 75, 76).
    """

    __tablename__ = "gst_return_snapshots"
    __table_args__ = (
        Index(
            "ix_gst_return_snapshots_unique_version",
            "return_period_id",
            "return_type",
            "version",
            unique=True,
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    return_period_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("gst_return_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    return_type: Mapped[GSTReturnType] = mapped_column(
        Enum(GSTReturnType, native_enum=False, length=10), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[GSTReturnSnapshotStatus] = mapped_column(
        Enum(GSTReturnSnapshotStatus, native_enum=False, length=20),
        default=GSTReturnSnapshotStatus.DRAFT,
        nullable=False,
        index=True,
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    summary_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
