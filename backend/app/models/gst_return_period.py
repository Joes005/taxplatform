from datetime import date

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.gst_enums import GSTReturnPeriodStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class GSTReturnPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A monthly GST return period (e.g. April 2026) a company prepares
    GSTR-1/GSTR-2B reconciliation/GSTR-3B against. Deliberately a separate
    entity from the bookkeeping-only `AccountingPeriod` — GST return status
    (OPEN/UNDER_REVIEW/FINALIZED/ARCHIVED) is a different lifecycle from
    ledger period locking.
    """

    __tablename__ = "gst_return_periods"
    __table_args__ = (
        Index(
            "ix_gst_return_periods_unique",
            "company_id",
            "year",
            "month",
            unique=True,
        ),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_gst_return_periods_month_range"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[GSTReturnPeriodStatus] = mapped_column(
        Enum(GSTReturnPeriodStatus, native_enum=False, length=15),
        default=GSTReturnPeriodStatus.OPEN,
        nullable=False,
        index=True,
    )
