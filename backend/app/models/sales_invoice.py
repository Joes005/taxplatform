from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.accounting_enums import DataSource, TransactionStatus
from app.models.mixins import MONEY, QUANTITY, RATE, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.customer import Customer


class SalesInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A GST tax invoice issued to a customer. `invoice_number` is unique
    per (company, financial year) — not globally — because different
    companies (and often different years) legitimately reuse numbering
    sequences. Preserves everything a future GST module needs for GSTR-1
    (place of supply, tax split, HSN via line items) without this module
    doing any filing itself.
    """

    __tablename__ = "sales_invoices"
    __table_args__ = (
        Index(
            "ix_sales_invoices_unique_number",
            "company_id",
            "financial_year_id",
            "invoice_number",
            unique=True,
        ),
        Index("ix_sales_invoices_company_date", "company_id", "invoice_date"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)

    place_of_supply: Mapped[str | None] = mapped_column(String(100), nullable=True)
    place_of_supply_state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)

    export_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    shipping_bill_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipping_bill_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    port_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    discount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    taxable_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    cgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    igst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    cess_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    total_tax: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    round_off: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

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

    customer: Mapped["Customer"] = relationship("Customer")
    items: Mapped[list["SalesInvoiceItem"]] = relationship(
        "SalesInvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )


class SalesInvoiceItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sales_invoice_items"

    sales_invoice_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("sales_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_service_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("products_services.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    quantity: Mapped[Decimal] = mapped_column(QUANTITY, default=1, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    discount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
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

    invoice: Mapped["SalesInvoice"] = relationship("SalesInvoice", back_populates="items")
