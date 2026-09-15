from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.accounting_enums import BalanceType, OpeningBalanceAccountType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class OpeningBalance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The authoritative per-financial-year opening balance for a Ledger,
    Customer, or Vendor. `account_id` is a loose pointer (like
    DocumentLink's resource_id) rather than three separate nullable FKs,
    since exactly one of three unrelated tables is being referenced and a
    single indexed column keeps that simple. The unique constraint means a
    duplicate insert fails loudly instead of silently overwriting history —
    correcting one goes through an explicit update, never a second insert.
    """

    __tablename__ = "opening_balances"
    __table_args__ = (
        Index(
            "ix_opening_balances_unique",
            "company_id",
            "financial_year_id",
            "account_type",
            "account_id",
            unique=True,
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_type: Mapped[OpeningBalanceAccountType] = mapped_column(
        Enum(OpeningBalanceAccountType, native_enum=False, length=10), nullable=False
    )
    account_id: Mapped[str] = mapped_column(GUID(), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    balance_type: Mapped[BalanceType] = mapped_column(
        Enum(BalanceType, native_enum=False, length=10), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
