import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.accounting_enums import DataSource, PaymentMode, TransactionStatus


class ReceiptCreate(BaseModel):
    financial_year_id: uuid.UUID
    receipt_date: date
    receipt_number: str = Field(min_length=1, max_length=50)
    customer_id: uuid.UUID
    ledger_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    payment_mode: PaymentMode
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    source: DataSource = DataSource.MANUAL
    source_reference: str | None = Field(default=None, max_length=255)


class ReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_year_id: uuid.UUID
    receipt_date: date
    receipt_number: str
    customer_id: uuid.UUID
    ledger_id: uuid.UUID
    amount: Decimal
    payment_mode: PaymentMode
    reference_number: str | None
    notes: str | None
    status: TransactionStatus
    source: DataSource
    source_reference: str | None
    created_at: datetime
    updated_at: datetime
