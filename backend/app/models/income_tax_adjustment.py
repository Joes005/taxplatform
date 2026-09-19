import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import IncomeTaxSourceType, TaxAdjustmentType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class IncomeTaxAdjustment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One book-to-tax adjustment against business/professional income
    (PHASE8 §26). `difference` (`tax_amount - book_amount`) is what
    `BusinessIncomeCalculationService` actually adds to (or subtracts
    from) book profit — `adjustment_type` is classification/reporting
    metadata only, so the arithmetic never depends on getting the
    ADD_BACK/DEDUCTION direction right in two different places.
    """

    __tablename__ = "income_tax_adjustments"
    __table_args__ = (Index("ix_income_tax_adjustments_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    adjustment_type: Mapped[TaxAdjustmentType] = mapped_column(
        Enum(TaxAdjustmentType, native_enum=False, length=25), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    book_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    difference: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    source_type: Mapped[IncomeTaxSourceType | None] = mapped_column(
        Enum(IncomeTaxSourceType, native_enum=False, length=20), nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
