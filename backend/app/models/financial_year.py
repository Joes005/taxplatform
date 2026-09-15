from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.accounting_enums import FinancialYearStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class FinancialYear(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An Indian financial year (e.g. "2025-26" = 1 Apr 2025 - 31 Mar 2026).
    Every accounting transaction belongs to exactly one financial year, and
    a company has at most one *current* financial year at a time.
    """

    __tablename__ = "financial_years"
    __table_args__ = (
        Index(
            "ix_financial_years_unique_current",
            "company_id",
            unique=True,
            postgresql_where="is_current = true",
            sqlite_where="is_current = 1",
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[FinancialYearStatus] = mapped_column(
        Enum(FinancialYearStatus, native_enum=False, length=10),
        default=FinancialYearStatus.OPEN,
        nullable=False,
    )

    def contains(self, on_date: date) -> bool:
        return self.start_date <= on_date <= self.end_date
