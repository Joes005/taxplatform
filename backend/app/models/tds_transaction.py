import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.accounting_enums import DataSource
from app.models.mixins import MONEY, RATE, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tds_enums import PANStatus, TDSApplicabilityStatus, TDSTransactionStatus
from app.utils.types import GUID


class TDSTransactionSourceType:
    PAYMENT = "PAYMENT"
    PURCHASE_INVOICE = "PURCHASE_INVOICE"


class TDSTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One TDS deduction decision against one payment/expense.

    `source_type`/`source_id` trace back to the accounting record this
    deduction is against (a Payment or PurchaseInvoice) without duplicating
    it (PHASE5 section 18) — `source`/`source_reference` separately record
    how *this* TDSTransaction row itself was created (typed manually vs.
    from an import job), the same distinction Phase 3's Payment/
    PurchaseInvoice already make about themselves.

    `system_calculated_amount` is never overwritten by a manual override
    (PHASE5 section 50) — `tds_amount` is what's actually deducted/used
    everywhere else, `system_calculated_amount` is what the engine said,
    so an auditor can always see whether — and by how much — a human
    changed the system's answer.
    """

    __tablename__ = "tds_transactions"
    __table_args__ = (
        Index("ix_tds_transactions_company_status", "company_id", "status"),
        Index("ix_tds_transactions_company_date", "company_id", "transaction_date"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    deductee_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("deductees.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tds_section_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("tds_sections.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tds_rule_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("tds_rules.id", ondelete="SET NULL"), nullable=True
    )

    source_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    source: Mapped[DataSource] = mapped_column(
        Enum(DataSource, native_enum=False, length=10), default=DataSource.MANUAL, nullable=False
    )
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    deduction_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    gross_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    taxable_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    tds_rate: Mapped[Decimal] = mapped_column(RATE, default=0, nullable=False)
    tds_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    pan_status: Mapped[PANStatus] = mapped_column(
        Enum(PANStatus, native_enum=False, length=15), default=PANStatus.NOT_AVAILABLE, nullable=False
    )
    applicability_status: Mapped[TDSApplicabilityStatus | None] = mapped_column(
        Enum(TDSApplicabilityStatus, native_enum=False, length=20), nullable=True
    )
    applicability_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    system_calculated_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    is_manual_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overridden_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[TDSTransactionStatus] = mapped_column(
        Enum(TDSTransactionStatus, native_enum=False, length=20),
        default=TDSTransactionStatus.DRAFT,
        nullable=False,
        index=True,
    )
