import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.bank_enums import BankStatementSourceType, BankStatementStatus


class BankStatementCreate(BaseModel):
    bank_account_id: uuid.UUID
    statement_name: str = Field(min_length=1, max_length=255)
    period_start: date
    period_end: date
    opening_balance: Decimal
    closing_balance: Decimal
    source_type: BankStatementSourceType = BankStatementSourceType.CSV

    @model_validator(mode="after")
    def check_dates(self) -> "BankStatementCreate":
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        return self


class BankStatementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    bank_account_id: uuid.UUID
    statement_name: str
    period_start: date
    period_end: date
    opening_balance: Decimal
    closing_balance: Decimal
    source_type: BankStatementSourceType
    source_document_id: uuid.UUID | None
    status: BankStatementStatus
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class BankStatementBalanceCheck(BaseModel):
    opening_balance: Decimal
    closing_balance: Decimal
    total_debits: Decimal
    total_credits: Decimal
    expected_closing_balance: Decimal
    difference: Decimal
    balanced: bool
