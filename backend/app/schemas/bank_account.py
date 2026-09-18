import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.bank_enums import BankAccountType


class BankAccountCreate(BaseModel):
    bank_name: str = Field(min_length=1, max_length=255)
    branch_name: str | None = Field(default=None, max_length=255)
    account_name: str = Field(min_length=1, max_length=255)
    account_number_masked: str = Field(min_length=1, max_length=30)
    account_type: BankAccountType = BankAccountType.CURRENT
    ifsc_code: str | None = Field(default=None, max_length=11)
    currency: str = Field(default="INR", max_length=3)
    opening_balance: Decimal = Field(default=Decimal("0"))
    opening_balance_date: date
    ledger_id: uuid.UUID | None = None


class BankAccountUpdate(BaseModel):
    bank_name: str | None = Field(default=None, min_length=1, max_length=255)
    branch_name: str | None = Field(default=None, max_length=255)
    account_name: str | None = Field(default=None, min_length=1, max_length=255)
    account_type: BankAccountType | None = None
    ifsc_code: str | None = Field(default=None, max_length=11)
    ledger_id: uuid.UUID | None = None
    is_active: bool | None = None


class BankAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    ledger_id: uuid.UUID | None
    bank_name: str
    branch_name: str | None
    account_name: str
    account_number_masked: str
    account_type: BankAccountType
    ifsc_code: str | None
    currency: str
    opening_balance: Decimal
    opening_balance_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime
