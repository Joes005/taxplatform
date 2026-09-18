from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tds_enums import TDSReconciliationStatus
from app.utils.types import GUID


class TDSPaymentReconciliation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One finding from a reconciliation run comparing TDS deducted against
    challan allocations (PHASE5 section 23). A row centers on either a
    transaction (`tds_transaction_id` set — is its deduction fully covered
    by challan payments?) or a challan (`tds_challan_id` set — does the
    challan still have money nothing has been allocated to?), never both,
    mirroring how a mismatch can originate from either side.

    Rows are fully recomputed on every run — this table is a report, not a
    ledger a user edits directly.
    """

    __tablename__ = "tds_payment_reconciliations"
    __table_args__ = (
        Index("ix_tds_payment_reconciliations_company_fy", "company_id", "financial_year_id"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tds_transaction_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("tds_transactions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    tds_challan_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("tds_challans.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[TDSReconciliationStatus] = mapped_column(
        Enum(TDSReconciliationStatus, native_enum=False, length=20), nullable=False, index=True
    )
    expected_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    allocated_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    variance_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
