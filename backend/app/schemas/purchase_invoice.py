import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.accounting_enums import DataSource, TransactionStatus


class PurchaseInvoiceItemCreate(BaseModel):
    product_service_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=500)
    quantity: Annotated[Decimal, Field(gt=0)]
    unit: str | None = Field(default=None, max_length=20)
    unit_price: Annotated[Decimal, Field(ge=0)]
    discount: Annotated[Decimal, Field(ge=0)] = Decimal("0")
    cgst_rate: Annotated[Decimal, Field(ge=0, le=100)] = Decimal("0")
    sgst_rate: Annotated[Decimal, Field(ge=0, le=100)] = Decimal("0")
    igst_rate: Annotated[Decimal, Field(ge=0, le=100)] = Decimal("0")
    cess_rate: Annotated[Decimal, Field(ge=0, le=100)] = Decimal("0")


class PurchaseInvoiceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_service_id: uuid.UUID | None
    description: str | None
    quantity: Decimal
    unit: str | None
    unit_price: Decimal
    discount: Decimal
    taxable_value: Decimal
    tax_rate: Decimal
    cgst_rate: Decimal
    sgst_rate: Decimal
    igst_rate: Decimal
    cess_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_amount: Decimal


class PurchaseInvoiceCreate(BaseModel):
    financial_year_id: uuid.UUID
    vendor_id: uuid.UUID
    invoice_number: str = Field(min_length=1, max_length=50)
    invoice_date: date
    supplier_invoice_number: str | None = Field(default=None, max_length=50)
    supplier_invoice_date: date | None = None
    place_of_supply: str | None = Field(default=None, max_length=100)
    discount: Annotated[Decimal, Field(ge=0)] = Decimal("0")
    items: list[PurchaseInvoiceItemCreate] = Field(min_length=1)
    source: DataSource = DataSource.MANUAL
    source_reference: str | None = Field(default=None, max_length=255)


class PurchaseInvoiceUpdate(BaseModel):
    vendor_id: uuid.UUID | None = None
    invoice_number: str | None = Field(default=None, min_length=1, max_length=50)
    invoice_date: date | None = None
    supplier_invoice_number: str | None = Field(default=None, max_length=50)
    supplier_invoice_date: date | None = None
    place_of_supply: str | None = Field(default=None, max_length=100)
    discount: Annotated[Decimal | None, Field(default=None, ge=0)] = None
    items: list[PurchaseInvoiceItemCreate] | None = None


class PurchaseInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_year_id: uuid.UUID
    vendor_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    supplier_invoice_number: str | None
    supplier_invoice_date: date | None
    place_of_supply: str | None
    subtotal: Decimal
    discount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    grand_total: Decimal
    status: TransactionStatus
    source: DataSource
    source_reference: str | None
    items: list[PurchaseInvoiceItemRead]
    created_at: datetime
    updated_at: datetime
