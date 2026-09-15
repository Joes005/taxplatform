from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.accounting_enums import DataSource, NoteType, TransactionStatus
from app.models.mixins import MONEY, QUANTITY, RATE, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.vendor import Vendor


class DebitNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Increases a previously issued Sales or Purchase invoice's value —
    the mirror image of CreditNote. Same note_type/party/reference shape.
    """

    __tablename__ = "debit_notes"
    __table_args__ = (
        Index(
            "ix_debit_notes_unique_number",
            "company_id",
            "financial_year_id",
            "debit_note_number",
            unique=True,
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    note_type: Mapped[NoteType] = mapped_column(
        Enum(NoteType, native_enum=False, length=10), nullable=False
    )
    customer_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True
    )
    vendor_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=True
    )
    reference_sales_invoice_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("sales_invoices.id", ondelete="SET NULL"), nullable=True
    )
    reference_purchase_invoice_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("purchase_invoices.id", ondelete="SET NULL"), nullable=True
    )

    debit_note_number: Mapped[str] = mapped_column(String(50), nullable=False)
    debit_note_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    taxable_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    igst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    cess_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

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

    customer: Mapped["Customer | None"] = relationship("Customer")
    vendor: Mapped["Vendor | None"] = relationship("Vendor")
    items: Mapped[list["DebitNoteItem"]] = relationship(
        "DebitNoteItem", back_populates="debit_note", cascade="all, delete-orphan"
    )


class DebitNoteItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "debit_note_items"

    debit_note_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("debit_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_service_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("products_services.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    quantity: Mapped[Decimal] = mapped_column(QUANTITY, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    taxable_value: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    tax_rate: Mapped[Decimal] = mapped_column(RATE, default=0, nullable=False)
    cgst_rate: Mapped[Decimal] = mapped_column(RATE, default=0, nullable=False)
    sgst_rate: Mapped[Decimal] = mapped_column(RATE, default=0, nullable=False)
    igst_rate: Mapped[Decimal] = mapped_column(RATE, default=0, nullable=False)
    cess_rate: Mapped[Decimal] = mapped_column(RATE, default=0, nullable=False)

    cgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    igst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    cess_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    debit_note: Mapped["DebitNote"] = relationship("DebitNote", back_populates="items")
