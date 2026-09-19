import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import TaxLossType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class IncomeTaxLoss(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One loss originating in `origin_financial_year_id` (PHASE8 §30).

    `IncomeTaxLossService` applies a loss against eligible positive income
    heads only within the *same* financial year it was recorded for
    (current-year set-off) and updates `setoff_amount`/
    `carried_forward_amount` accordingly. Automatically re-applying a
    carried-forward balance against a *later* year's computation is a
    deliberately deferred next iteration (PHASE8 §30 allows configurable
    carry-forward; this cut tracks the balance and its
    `expiry_financial_year_id` but does not yet auto-consume it in a
    future computation) — the balance is always visible, never silently
    dropped, but re-applying it today requires a manual review step.
    """

    __tablename__ = "income_tax_losses"
    __table_args__ = (Index("ix_income_tax_losses_company_fy", "company_id", "origin_financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    origin_financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    loss_type: Mapped[TaxLossType] = mapped_column(Enum(TaxLossType, native_enum=False, length=20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    setoff_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    carried_forward_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    expiry_financial_year_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
