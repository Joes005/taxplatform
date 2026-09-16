import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.gst_enums import ITCCategory, ITCReviewStatus, ReconciliationStatus
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class GSTReconciliation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One reconciliation run (Purchase Books vs. imported GSTR-2B) for a
    return period. Re-running replaces the prior run's result rows rather
    than accumulating duplicates, but the run header itself is kept for a
    dashboard history of match rates over time.
    """

    __tablename__ = "gst_reconciliations"

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    return_period_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("gst_return_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    total_purchase_invoices: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    partially_matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mismatch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    books_only_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gstr2b_only_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_required_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    results: Mapped[list["GSTReconciliationResult"]] = relationship(
        "GSTReconciliationResult", back_populates="reconciliation", cascade="all, delete-orphan"
    )


class GSTReconciliationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One books-vs-GSTR-2B comparison row. Exactly one of
    `purchase_invoice_id`/`gstr2b_record_id` is null for a BOOKS_ONLY or
    GSTR2B_ONLY result; both are populated once matched. This row is also
    the traceable source of an ITC figure: ITC Record -> this row ->
    PurchaseInvoice (PHASE4 section 80).
    """

    __tablename__ = "gst_reconciliation_results"
    __table_args__ = (
        Index("ix_gst_reconciliation_results_reconciliation", "reconciliation_id", "status"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reconciliation_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("gst_reconciliations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purchase_invoice_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("purchase_invoices.id", ondelete="SET NULL"), nullable=True
    )
    gstr2b_record_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("gstr2b_records.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus, native_enum=False, length=30), nullable=False, index=True
    )

    books_taxable_value: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    books_cgst_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    books_sgst_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    books_igst_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    books_cess_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)

    gstr2b_taxable_value: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    gstr2b_cgst_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    gstr2b_sgst_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    gstr2b_igst_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    gstr2b_cess_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)

    taxable_value_diff: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    tax_diff: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)

    itc_category: Mapped[ITCCategory | None] = mapped_column(
        Enum(ITCCategory, native_enum=False, length=20), nullable=True, index=True
    )
    itc_review_status: Mapped[ITCReviewStatus] = mapped_column(
        Enum(ITCReviewStatus, native_enum=False, length=15),
        default=ITCReviewStatus.PENDING,
        nullable=False,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    reconciliation: Mapped["GSTReconciliation"] = relationship(
        "GSTReconciliation", back_populates="results"
    )
