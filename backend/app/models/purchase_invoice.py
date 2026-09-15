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
    from app.models.vendor import Vendor


class PurchaseInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A bill received from a vendor. `invoice_number` is Tally Tax's own
    internal reference; `supplier_invoice_number`/`_date` preserve the
    vendor's own numbering — GSTR-2B reconciliation later matches on the
    supplier's invoice details, not ours.
    """

    __tablename__ = "purchase_invoices"
    __table_args__ = (
        Index(
            "ix_purchase_invoices_unique_number",
            "company_id",
            "financial_year_id",
            "invoice_number",
            unique=True,
        ),
        Index("ix_purchase_invoices_company_date", "company_id", "invoice_date"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    vendor_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_invoice_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    supplier_invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    place_of_supply: Mapped[str | None] = mapped_column(String(100), nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    discount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    taxable_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    cgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    igst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    cess_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    total_tax: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

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

    vendor: Mapped["Vendor"] = relationship("Vendor")
    items: Mapped[list["PurchaseInvoiceItem"]] = relationship(
        "PurchaseInvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )


class PurchaseInvoiceItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "purchase_invoice_items"

    purchase_invoice_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("purchase_invoices.id", ondelete="CASCADE"), nullable=False, index=True
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

    invoice: Mapped["PurchaseInvoice"] = relationship("PurchaseInvoice", back_populates="items")
