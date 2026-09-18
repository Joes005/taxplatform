from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.bank_enums import BankAccountType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class BankAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A company's bank account, tracked for reconciliation only — this
    platform never connects to the bank itself (PHASE6 §63). Only a
    masked account number is ever stored/accepted (PHASE6 §7); the full
    number is never collected, so there is nothing sensitive to leak from
    logs, the API, or the UI. `ledger_id` optionally links to the Phase 3
    Ledger this account is booked under, so "book balance" can be read
    from the real chart of accounts instead of a second, parallel balance
    this module would have to keep in sync itself.
    """

    __tablename__ = "bank_accounts"
    __table_args__ = (
        Index(
            "ix_bank_accounts_company_number",
            "company_id",
            "account_number_masked",
            unique=True,
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ledger_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("ledgers.id", ondelete="SET NULL"), nullable=True
    )
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number_masked: Mapped[str] = mapped_column(String(30), nullable=False)
    account_type: Mapped[BankAccountType] = mapped_column(
        Enum(BankAccountType, native_enum=False, length=15),
        default=BankAccountType.CURRENT,
        nullable=False,
    )
    ifsc_code: Mapped[str | None] = mapped_column(String(11), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    opening_balance_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
