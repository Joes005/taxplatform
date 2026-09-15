from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.accounting_enums import PeriodStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.financial_year import FinancialYear


class AccountingPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A sub-division of a financial year (typically one calendar month)
    used to progressively close the books. A CLOSED or LOCKED period blocks
    new/edited transactions dated within it — see
    AccountingPeriodService.assert_period_open.
    """

    __tablename__ = "accounting_periods"

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PeriodStatus] = mapped_column(
        Enum(PeriodStatus, native_enum=False, length=10), default=PeriodStatus.OPEN, nullable=False
    )

    financial_year: Mapped["FinancialYear"] = relationship("FinancialYear")

    def contains(self, on_date: date) -> bool:
        return self.start_date <= on_date <= self.end_date
