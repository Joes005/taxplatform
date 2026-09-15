import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.accounting_enums import BalanceType, OpeningBalanceAccountType


class OpeningBalanceCreate(BaseModel):
    financial_year_id: uuid.UUID
    account_type: OpeningBalanceAccountType
    account_id: uuid.UUID
    amount: Decimal = Field(ge=0)
    balance_type: BalanceType
    notes: str | None = Field(default=None, max_length=255)


class OpeningBalanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_year_id: uuid.UUID
    account_type: OpeningBalanceAccountType
    account_id: uuid.UUID
    amount: Decimal
    balance_type: BalanceType
    notes: str | None
    created_at: datetime
    updated_at: datetime
