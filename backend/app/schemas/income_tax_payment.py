import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class IncomeTaxPaymentCreate(BaseModel):
    financial_year_id: uuid.UUID
    payment_date: date
    amount: Decimal
    challan_number: str | None = Field(default=None, max_length=50)


class IncomeTaxPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    payment_date: date
    amount: Decimal
    challan_number: str | None
    created_by: uuid.UUID
