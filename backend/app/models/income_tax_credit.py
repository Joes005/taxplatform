import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import IncomeTaxSourceType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class IncomeTaxCreditEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """TDS/TCS credit *received* by this company — tax a customer or bank
    deducted on income paid to this company, the Form 26AS-style asset
    against this company's own tax liability (PHASE8 §36-37).

    This is deliberately a new, minimal model rather than a reuse of
    Phase 5's `TDSTransaction`: that table records TDS *this company
    deducts from its own vendors* (an outgoing liability tracked toward
    24Q/26Q filing) — a different direction of money and a different
    legal event from tax credit the company itself receives. Reusing it
    here would conflate the two. No live Form 26AS/AIS fetch is performed
    anywhere in this platform — every row here is manually entered or
    derived from an existing local record via `source_type`/`source_id`.
    """

    __tablename__ = "income_tax_credit_entries"
    __table_args__ = (Index("ix_income_tax_credit_entries_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    deductor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    deductor_tan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    section_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    certificate_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_type: Mapped[IncomeTaxSourceType | None] = mapped_column(
        Enum(IncomeTaxSourceType, native_enum=False, length=20), nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
