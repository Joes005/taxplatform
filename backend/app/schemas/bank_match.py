import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.bank_enums import BankMatchSourceType, BankMatchStatus, BankMatchType


class BankMatchCandidate(BaseModel):
    source_type: BankMatchSourceType
    source_id: uuid.UUID
    label: str
    source_date: date
    source_amount: Decimal
    counterparty_name: str | None
    reference_number: str | None
    score: int
    confidence: str


class ManualMatchCreate(BaseModel):
    source_type: BankMatchSourceType
    source_id: uuid.UUID
    matched_amount: Decimal = Field(gt=0)
    notes: str | None = Field(default=None, max_length=500)


class BankTransactionMatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    bank_transaction_id: uuid.UUID
    source_type: BankMatchSourceType
    source_id: uuid.UUID
    matched_amount: Decimal
    match_type: BankMatchType
    match_score: int | None
    status: BankMatchStatus
    matched_by: uuid.UUID
    matched_at: datetime
    notes: str | None
