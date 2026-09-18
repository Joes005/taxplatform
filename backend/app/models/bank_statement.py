from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.bank_enums import BankStatementSourceType, BankStatementStatus
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class BankStatement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One imported bank statement file/period. `source_document_id`
    reuses Phase 2's Document/StorageProvider for the underlying file —
    this module never re-implements file storage (PHASE6 §12).
    """

    __tablename__ = "bank_statements"

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_account_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("bank_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    statement_name: Mapped[str] = mapped_column(String(255), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    closing_balance: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    source_type: Mapped[BankStatementSourceType] = mapped_column(
        Enum(BankStatementSourceType, native_enum=False, length=10), nullable=False
    )
    source_document_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[BankStatementStatus] = mapped_column(
        Enum(BankStatementStatus, native_enum=False, length=15),
        default=BankStatementStatus.IMPORTED,
        nullable=False,
        index=True,
    )
    created_by: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
