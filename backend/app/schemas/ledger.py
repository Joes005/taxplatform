import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.accounting_enums import BalanceType, LedgerType


class LedgerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=50)
    ledger_type: LedgerType
    parent_ledger_id: uuid.UUID | None = None
    opening_balance: Decimal = Decimal("0")
    opening_balance_type: BalanceType = BalanceType.DEBIT


class LedgerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=50)
    ledger_type: LedgerType | None = None
    parent_ledger_id: uuid.UUID | None = None
    opening_balance: Decimal | None = None
    opening_balance_type: BalanceType | None = None
    is_active: bool | None = None


class LedgerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str | None
    ledger_type: LedgerType
    parent_ledger_id: uuid.UUID | None
    opening_balance: Decimal
    opening_balance_type: BalanceType
    is_active: bool
    created_at: datetime
    updated_at: datetime
