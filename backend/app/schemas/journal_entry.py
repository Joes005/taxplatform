import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.accounting_enums import DataSource, TransactionStatus


class JournalEntryLineCreate(BaseModel):
    ledger_id: uuid.UUID
    debit_amount: Annotated[Decimal, Field(ge=0)] = Decimal("0")
    credit_amount: Annotated[Decimal, Field(ge=0)] = Decimal("0")
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_one_side(self) -> "JournalEntryLineCreate":
        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValueError("A line cannot have both a debit and a credit amount")
        if self.debit_amount == 0 and self.credit_amount == 0:
            raise ValueError("A line must have either a debit or a credit amount")
        return self


class JournalEntryLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ledger_id: uuid.UUID
    debit_amount: Decimal
    credit_amount: Decimal
    description: str | None


class JournalEntryCreate(BaseModel):
    financial_year_id: uuid.UUID
    journal_number: str = Field(min_length=1, max_length=50)
    journal_date: date
    narration: str | None = Field(default=None, max_length=500)
    lines: list[JournalEntryLineCreate] = Field(min_length=2)
    source: DataSource = DataSource.MANUAL
    source_reference: str | None = Field(default=None, max_length=255)


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_year_id: uuid.UUID
    journal_number: str
    journal_date: date
    narration: str | None
    status: TransactionStatus
    source: DataSource
    source_reference: str | None
    lines: list[JournalEntryLineRead]
    created_at: datetime
    updated_at: datetime
