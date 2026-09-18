import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tds_enums import TDSReturnSnapshotStatus, TDSReturnType
from app.utils.types import GUID


class TDSReturnSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A point-in-time, versioned copy of a generated TDS return
    preparation — the TDS analogue of `GSTReturnSnapshot`. TDS
    transactions are mutable (a deductee's PAN can be corrected, an
    override applied) up until finalization, so a return preparation must
    be snapshotted rather than only ever recomputed live, exactly for the
    reason PHASE4's GST snapshot exists.
    """

    __tablename__ = "tds_return_snapshots"
    __table_args__ = (
        Index(
            "ix_tds_return_snapshots_unique_version",
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
        GUID(), ForeignKey("tds_return_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    return_type: Mapped[TDSReturnType] = mapped_column(
        Enum(TDSReturnType, native_enum=False, length=15), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TDSReturnSnapshotStatus] = mapped_column(
        Enum(TDSReturnSnapshotStatus, native_enum=False, length=20),
        default=TDSReturnSnapshotStatus.DRAFT,
        nullable=False,
        index=True,
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    summary_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
