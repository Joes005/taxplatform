"""Salary, house-property, other-sources, and exempt income entries
(PHASE8 §21-22, §28-29). Each row is scoped to `(company_id,
financial_year_id)` — the same convention Phase 3/5 already use for
`SalesInvoice`/`TDSTransaction` — rather than to one specific
`TaxComputation`, so income can be entered once and a computation always
picks up the latest state when (re)calculated. `TaxComputationSnapshot`
is what actually freezes a point-in-time copy (PHASE8 §41).
"""

from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import HousePropertyType, IncomeTaxSourceType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class IncomeTaxSalaryIncome(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "income_tax_salary_incomes"
    __table_args__ = (Index("ix_income_tax_salary_incomes_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    employer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gross_salary: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    allowances: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    perquisites: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    profit_in_lieu: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    standard_deduction: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    professional_tax: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    tds: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    taxable_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)


class IncomeTaxHousePropertyIncome(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "income_tax_house_property_incomes"
    __table_args__ = (Index("ix_income_tax_house_property_incomes_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    property_type: Mapped[HousePropertyType] = mapped_column(
        Enum(HousePropertyType, native_enum=False, length=15), nullable=False
    )
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gross_rent: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    municipal_tax: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    net_annual_value: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    standard_deduction: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    interest_on_home_loan: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    income_or_loss: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)


class IncomeTaxOtherIncome(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "income_tax_other_incomes"
    __table_args__ = (Index("ix_income_tax_other_incomes_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    income_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    tds: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    source_type: Mapped[IncomeTaxSourceType | None] = mapped_column(
        Enum(IncomeTaxSourceType, native_enum=False, length=20), nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)


class IncomeTaxExemptIncome(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracked for disclosure only — never added into any taxable total
    (PHASE8 §29)."""

    __tablename__ = "income_tax_exempt_incomes"
    __table_args__ = (Index("ix_income_tax_exempt_incomes_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    section_code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
