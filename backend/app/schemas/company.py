import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    legal_name: Annotated[str, Field(min_length=1, max_length=255)]
    trade_name: Annotated[str | None, Field(default=None, max_length=255)]
    business_type: Annotated[str | None, Field(default=None, max_length=100)]
    pan: Annotated[str | None, Field(default=None, max_length=10)]
    gstin: Annotated[str | None, Field(default=None, max_length=15)]
    tan: Annotated[str | None, Field(default=None, max_length=10)]
    state: Annotated[str | None, Field(default=None, max_length=100)]
    city: Annotated[str | None, Field(default=None, max_length=100)]
    address: Annotated[str | None, Field(default=None, max_length=500)]
    financial_year_start: date | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    legal_name: Annotated[str | None, Field(default=None, min_length=1, max_length=255)]
    trade_name: Annotated[str | None, Field(default=None, max_length=255)]
    business_type: Annotated[str | None, Field(default=None, max_length=100)]
    pan: Annotated[str | None, Field(default=None, max_length=10)]
    gstin: Annotated[str | None, Field(default=None, max_length=15)]
    tan: Annotated[str | None, Field(default=None, max_length=10)]
    state: Annotated[str | None, Field(default=None, max_length=100)]
    city: Annotated[str | None, Field(default=None, max_length=100)]
    address: Annotated[str | None, Field(default=None, max_length=500)]
    financial_year_start: date | None = None
    is_active: bool | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
