from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.accounting_enums import DataSource, TransactionStatus
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.ledger import Ledger


class JournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The catch-all double-entry transaction. Balance (sum(debit) ==
    sum(credit) across `lines`) is validated by JournalEntryService at
    creation time — see app/services/journal_entry_service.py — so an
    unbalanced entry is never persisted in the first place, DRAFT or not.
    """

    __tablename__ = "journal_entries"
    __table_args__ = (
        Index(
            "ix_journal_entries_unique_number",
            "company_id",
            "financial_year_id",
            "journal_number",
            unique=True,
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    journal_number: Mapped[str] = mapped_column(String(50), nullable=False)
    journal_date: Mapped[date] = mapped_column(Date, nullable=False)
    narration: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, native_enum=False, length=10),
        default=TransactionStatus.DRAFT,
        nullable=False,
        index=True,
    )
    source: Mapped[DataSource] = mapped_column(
        Enum(DataSource, native_enum=False, length=10), default=DataSource.MANUAL, nullable=False
    )
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    lines: Mapped[list["JournalEntryLine"]] = relationship(
        "JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan"
    )


class JournalEntryLine(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "journal_entry_lines"

    journal_entry_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ledger_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("ledgers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    debit_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    journal_entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="lines")
    ledger: Mapped["Ledger"] = relationship("Ledger")
