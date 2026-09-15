import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.accounting_enums import DataSource, PartyType, PaymentMode, TransactionStatus


class PaymentCreate(BaseModel):
    financial_year_id: uuid.UUID
    payment_date: date
    payment_number: str = Field(min_length=1, max_length=50)
    party_type: PartyType | None = None
    party_id: uuid.UUID | None = None
    ledger_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    payment_mode: PaymentMode
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    source: DataSource = DataSource.MANUAL
    source_reference: str | None = Field(default=None, max_length=255)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_year_id: uuid.UUID
    payment_date: date
    payment_number: str
    party_type: PartyType | None
    party_id: uuid.UUID | None
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
