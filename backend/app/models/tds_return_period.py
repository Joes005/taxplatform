from datetime import date

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tds_enums import TDSQuarter, TDSReturnPeriodStatus
from app.utils.types import GUID


class TDSReturnPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A quarterly TDS return period (Q1-Q4 of a financial year) a company
    prepares its TDS return data against — the TDS analogue of Phase 4's
    `GSTReturnPeriod`, quarterly rather than monthly because TDS returns
    (24Q/26Q/27Q/27EQ) are filed quarterly, not monthly.
    """

    __tablename__ = "tds_return_periods"
    __table_args__ = (
        Index("ix_tds_return_periods_unique", "company_id", "financial_year_id", "quarter", unique=True),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quarter: Mapped[TDSQuarter] = mapped_column(Enum(TDSQuarter, native_enum=False, length=2), nullable=False)
    period_start: Mapped[date] = mapped_column(nullable=False)
    period_end: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[TDSReturnPeriodStatus] = mapped_column(
        Enum(TDSReturnPeriodStatus, native_enum=False, length=15),
        default=TDSReturnPeriodStatus.OPEN,
        nullable=False,
        index=True,
    )
