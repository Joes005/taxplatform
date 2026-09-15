from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.accounting_enums import BalanceType, LedgerType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class Ledger(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One accounting account (Tally calls this a "Ledger"). Every
    transaction in the system ultimately debits/credits one or more
    Ledgers by equal amounts — this is the chart of accounts.
    `parent_ledger_id` gives a two-level-or-deeper grouping hierarchy
    (e.g. "Rent" under "Indirect Expenses" under "Expenses"), mirroring
    how Tally organizes ledgers under groups.
    """

    __tablename__ = "ledgers"
    __table_args__ = (
        Index("ix_ledgers_company_name", "company_id", "name", unique=True),
        Index("ix_ledgers_company_code", "company_id", "code", unique=True),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ledger_type: Mapped[LedgerType] = mapped_column(
        Enum(LedgerType, native_enum=False, length=20), nullable=False, index=True
    )
    parent_ledger_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("ledgers.id", ondelete="SET NULL"), nullable=True
    )
    opening_balance: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    opening_balance_type: Mapped[BalanceType] = mapped_column(
        Enum(BalanceType, native_enum=False, length=10), default=BalanceType.DEBIT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped["Ledger | None"] = relationship("Ledger", remote_side="Ledger.id")
