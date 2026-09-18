import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.bank_enums import BankReconciliationStatus
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class BankReconciliation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One reconciliation session for a bank account over a period —
    the review workflow's unit of work (PHASE6 §16, §30):
    OPEN -> IN_PROGRESS -> PENDING_REVIEW -> RECONCILED -> LOCKED, with
    CANCELLED reachable early. `book_balance`/`bank_balance`/`difference`
    are snapshotted when computed (via `run-matching`/recompute), not
    live-joined on every read, so a reviewer's screen doesn't change
    under them mid-review.
    """

    __tablename__ = "bank_reconciliations"
    __table_args__ = (
        Index("ix_bank_reconciliations_company_account", "company_id", "bank_account_id"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_account_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("bank_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    opening_balance: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    closing_balance: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    book_balance: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    bank_balance: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    difference: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)

    status: Mapped[BankReconciliationStatus] = mapped_column(
        Enum(BankReconciliationStatus, native_enum=False, length=15),
        default=BankReconciliationStatus.OPEN,
        nullable=False,
        index=True,
    )
    started_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
