from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.bank_enums import BankTransactionReconciliationStatus, BankTransactionType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class BankTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row from an imported bank statement. `description` is always
    the bank's own original text, never overwritten — `normalized_description`/
    `normalized_reference` are separate columns the matching engine reads,
    so normalization is never destructive (PHASE6 §11). `checksum` is a
    deterministic hash of (company, bank_account, date, amount, reference,
    description) used for duplicate detection both within one import batch
    and against previously imported transactions (PHASE6 §15).
    """

    __tablename__ = "bank_transactions"
    __table_args__ = (
        Index(
            "ix_bank_transactions_unique_checksum",
            "company_id",
            "bank_account_id",
            "checksum",
            unique=True,
        ),
        Index("ix_bank_transactions_company_account_date", "company_id", "bank_account_id", "transaction_date"),
        CheckConstraint("debit_amount >= 0", name="ck_bank_transactions_debit_non_negative"),
        CheckConstraint("credit_amount >= 0", name="ck_bank_transactions_credit_non_negative"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_statement_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_account_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("bank_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cheque_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    debit_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    balance_after_transaction: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)

    transaction_type: Mapped[BankTransactionType] = mapped_column(
        Enum(BankTransactionType, native_enum=False, length=10), nullable=False, index=True
    )

    normalized_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    normalized_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    external_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    reconciliation_status: Mapped[BankTransactionReconciliationStatus] = mapped_column(
        Enum(BankTransactionReconciliationStatus, native_enum=False, length=20),
        default=BankTransactionReconciliationStatus.UNMATCHED,
        nullable=False,
        index=True,
    )
