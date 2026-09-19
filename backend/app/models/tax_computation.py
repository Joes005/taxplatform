import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import TaxComputationStatus, TaxRegime
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class TaxComputation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The central Income Tax computation for one company/financial year
    (PHASE8 §31, §41-42). Income/deduction/credit totals here are always
    recomputed live from the underlying `(company_id, financial_year_id)`-
    scoped rows by `IncomeTaxComputationService.calculate()` until the
    computation is `LOCKED` — `TaxComputationSnapshot` is what actually
    freezes a reproducible, point-in-time copy for history.
    """

    __tablename__ = "tax_computations"
    __table_args__ = (Index("ix_tax_computations_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assessment_year: Mapped[str] = mapped_column(String(10), nullable=False)
    tax_regime: Mapped[TaxRegime] = mapped_column(Enum(TaxRegime, native_enum=False, length=15), nullable=False)
    rule_set_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("income_tax_rule_sets.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[TaxComputationStatus] = mapped_column(
        Enum(TaxComputationStatus, native_enum=False, length=20),
        default=TaxComputationStatus.DRAFT,
        nullable=False,
        index=True,
    )

    salary_income: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    house_property_income: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    business_income: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    capital_gains_income: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    other_income: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    gross_total_income: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    total_deductions: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    taxable_income: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    tax_before_rebate: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    rebate: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    tax_after_rebate: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    surcharge: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    cess: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    gross_tax_liability: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    tds_credit_total: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    advance_tax_total: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    self_assessment_tax_total: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    balance_payable_or_refund: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class TaxComputationSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A point-in-time, versioned copy of a calculated `TaxComputation` —
    the Income Tax analogue of `GSTReturnSnapshot`/`TDSReturnSnapshot`
    (PHASE8 §41, §71). Always records which `rule_set_id` produced it, so
    a later tax-law change never changes what a historical snapshot says.
    """

    __tablename__ = "tax_computation_snapshots"
    __table_args__ = (
        Index("ix_tax_computation_snapshots_unique_version", "tax_computation_id", "version", unique=True),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tax_computation_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("tax_computations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_set_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("income_tax_rule_sets.id", ondelete="RESTRICT"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    summary_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
