import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class IncomeTaxAdvanceTaxPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One advance-tax instalment paid outside this platform (PHASE8 §38)
    — recorded for computation purposes only; no challan is ever
    generated or submitted here."""

    __tablename__ = "income_tax_advance_tax_payments"
    __table_args__ = (Index("ix_income_tax_advance_tax_payments_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    challan_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class IncomeTaxSelfAssessmentTaxPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One self-assessment tax payment made outside this platform
    (PHASE8 §39) — same shape as `IncomeTaxAdvanceTaxPayment`, kept as a
    distinct table because the two appear as separate lines in the tax
    payment summary (PHASE8 §40) and are recorded at different points in
    the workflow (before vs. at/after return preparation)."""

    __tablename__ = "income_tax_self_assessment_tax_payments"
    __table_args__ = (
        Index("ix_income_tax_self_assessment_tax_payments_company_fy", "company_id", "financial_year_id"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    challan_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
