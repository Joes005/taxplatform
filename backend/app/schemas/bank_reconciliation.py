import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.bank_enums import BankReconciliationStatus


class BankReconciliationCreate(BaseModel):
    bank_account_id: uuid.UUID
    period_start: date
    period_end: date
    opening_balance: Decimal
    closing_balance: Decimal

    @model_validator(mode="after")
    def check_dates(self) -> "BankReconciliationCreate":
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        return self


class BankReconciliationActionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=500)


class BankReconciliationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    bank_account_id: uuid.UUID
    period_start: date
    period_end: date
    opening_balance: Decimal
    closing_balance: Decimal
    book_balance: Decimal | None
    bank_balance: Decimal | None
    difference: Decimal | None
    status: BankReconciliationStatus
    started_by: uuid.UUID
    reviewed_by: uuid.UUID | None
    started_at: datetime
    completed_at: datetime | None
    reviewed_at: datetime | None


class BankReconciliationSummary(BaseModel):
    reconciliation: BankReconciliationRead
    matched_count: int
    partially_matched_count: int
    unmatched_count: int
    review_required_count: int
    excluded_count: int
