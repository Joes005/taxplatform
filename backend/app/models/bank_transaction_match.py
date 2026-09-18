import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.bank_enums import BankMatchSourceType, BankMatchStatus, BankMatchType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class BankTransactionMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One claim that a bank transaction corresponds to (all or part of)
    one accounting record. `source_type`/`source_id` is a generic
    reference — like `TDSTransaction.source_type`/`source_id` — rather
    than three separate nullable FKs, because a match can point to a
    Payment, a Receipt, or a JournalEntry, and never more than one of
    them (PHASE6 §22). A bank transaction can have several ACTIVE matches
    (partial matching, §23); `BankMatchService` enforces that their sum
    never exceeds the bank transaction's own amount, and that reversing
    one sets `status=REVERSED` rather than deleting the row, so match
    history is never lost (PHASE6 §64).
    """

    __tablename__ = "bank_transaction_matches"
    __table_args__ = (
        Index("ix_bank_transaction_matches_bank_txn", "bank_transaction_id"),
        Index("ix_bank_transaction_matches_source", "source_type", "source_id"),
        CheckConstraint("matched_amount > 0", name="ck_bank_transaction_matches_amount_positive"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_transaction_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("bank_transactions.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[BankMatchSourceType] = mapped_column(
        Enum(BankMatchSourceType, native_enum=False, length=15), nullable=False
    )
    source_id: Mapped[str] = mapped_column(GUID(), nullable=False)
    matched_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    match_type: Mapped[BankMatchType] = mapped_column(
        Enum(BankMatchType, native_enum=False, length=10), nullable=False
    )
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[BankMatchStatus] = mapped_column(
        Enum(BankMatchStatus, native_enum=False, length=10),
        default=BankMatchStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    matched_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
