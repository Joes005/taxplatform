from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.accounting_enums import DataSource, PartyType, PaymentMode, TransactionStatus
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.ledger import Ledger


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Money paid out by the company — to a vendor, or to any other payee
    tracked only by ledger (e.g. rent, salary). `party_type`/`party_id`
    stay nullable together for an OTHER payment that isn't tied to a
    Vendor/Customer record at all.
    """

    __tablename__ = "payments"
    __table_args__ = (
        Index(
            "ix_payments_unique_number",
            "company_id",
            "financial_year_id",
            "payment_number",
            unique=True,
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_number: Mapped[str] = mapped_column(String(50), nullable=False)

    party_type: Mapped[PartyType | None] = mapped_column(
        Enum(PartyType, native_enum=False, length=10), nullable=True
    )
    party_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)

    ledger_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("ledgers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    payment_mode: Mapped[PaymentMode] = mapped_column(
        Enum(PaymentMode, native_enum=False, length=10), nullable=False
    )
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, native_enum=False, length=10),
        default=TransactionStatus.POSTED,
        nullable=False,
        index=True,
    )
    source: Mapped[DataSource] = mapped_column(
        Enum(DataSource, native_enum=False, length=10), default=DataSource.MANUAL, nullable=False
    )
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    ledger: Mapped["Ledger"] = relationship("Ledger")
