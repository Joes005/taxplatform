from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import IncomeTaxSourceType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class IncomeTaxDeduction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One Chapter VI-A-style deduction claim (PHASE8 §18-19).
    `eligible_amount` is always computed by `DeductionService` against the
    applicable `IncomeTaxDeductionRule` — `claimed_amount` is what the
    preparer entered, `eligible_amount` is what the computation actually
    uses, so a CA reviewing later can see whether — and by how much — a
    claim was capped, the same "never overwrite, always show both"
    principle `TDSTransaction.system_calculated_amount` already uses.
    """

    __tablename__ = "income_tax_deductions"
    __table_args__ = (Index("ix_income_tax_deductions_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    section_code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    claimed_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    eligible_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    source_type: Mapped[IncomeTaxSourceType | None] = mapped_column(
        Enum(IncomeTaxSourceType, native_enum=False, length=20), nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
