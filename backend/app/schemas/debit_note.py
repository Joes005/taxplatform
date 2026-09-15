import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.accounting_enums import DataSource, NoteType, TransactionStatus


class DebitNoteItemCreate(BaseModel):
    product_service_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=500)
    quantity: Annotated[Decimal, Field(gt=0)]
    unit_price: Annotated[Decimal, Field(ge=0)]
    cgst_rate: Annotated[Decimal, Field(ge=0, le=100)] = Decimal("0")
    sgst_rate: Annotated[Decimal, Field(ge=0, le=100)] = Decimal("0")
    igst_rate: Annotated[Decimal, Field(ge=0, le=100)] = Decimal("0")
    cess_rate: Annotated[Decimal, Field(ge=0, le=100)] = Decimal("0")


class DebitNoteItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_service_id: uuid.UUID | None
    description: str | None
    quantity: Decimal
    unit_price: Decimal
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


class DebitNoteCreate(BaseModel):
    financial_year_id: uuid.UUID
    note_type: NoteType
    customer_id: uuid.UUID | None = None
    vendor_id: uuid.UUID | None = None
    reference_sales_invoice_id: uuid.UUID | None = None
    reference_purchase_invoice_id: uuid.UUID | None = None
    debit_note_number: str = Field(min_length=1, max_length=50)
    debit_note_date: date
    reason: str | None = Field(default=None, max_length=500)
    items: list[DebitNoteItemCreate] = Field(min_length=1)
    source: DataSource = DataSource.MANUAL
    source_reference: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def check_party_matches_type(self) -> "DebitNoteCreate":
        if self.note_type == NoteType.SALES:
            if self.customer_id is None:
                raise ValueError("customer_id is required for a SALES debit note")
            self.vendor_id = None
        else:
            if self.vendor_id is None:
                raise ValueError("vendor_id is required for a PURCHASE debit note")
            self.customer_id = None
        return self


class DebitNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_year_id: uuid.UUID
    note_type: NoteType
    customer_id: uuid.UUID | None
    vendor_id: uuid.UUID | None
    reference_sales_invoice_id: uuid.UUID | None
    reference_purchase_invoice_id: uuid.UUID | None
    debit_note_number: str
    debit_note_date: date
    reason: str | None
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_amount: Decimal
    status: TransactionStatus
    source: DataSource
    source_reference: str | None
    items: list[DebitNoteItemRead]
    created_at: datetime
    updated_at: datetime
