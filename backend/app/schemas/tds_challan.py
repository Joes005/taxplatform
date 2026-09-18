import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.tds_enums import TDSChallanStatus


class TDSChallanCreate(BaseModel):
    challan_number: str = Field(min_length=1, max_length=50)
    challan_date: date
    amount: Decimal = Field(gt=0)
    financial_year_id: uuid.UUID
    bank_reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class TDSChallanUpdate(BaseModel):
    challan_number: str | None = Field(default=None, min_length=1, max_length=50)
    challan_date: date | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    status: TDSChallanStatus | None = None
    bank_reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class TDSChallanAllocateRequest(BaseModel):
    tds_transaction_id: uuid.UUID
    allocated_amount: Decimal = Field(gt=0)


class TDSChallanAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    challan_id: uuid.UUID
    tds_transaction_id: uuid.UUID
    allocated_amount: Decimal
    created_at: datetime


class TDSChallanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    challan_number: str
    challan_date: date
    amount: Decimal
    status: TDSChallanStatus
    bank_reference_number: str | None
    notes: str | None
    allocated_amount: Decimal
    unallocated_amount: Decimal
    created_at: datetime
    updated_at: datetime
