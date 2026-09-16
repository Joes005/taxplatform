import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GSTTaxRateCreate(BaseModel):
    rate: Decimal = Field(ge=0, le=100)
    description: str | None = Field(default=None, max_length=255)
    effective_from: date
    effective_to: date | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def check_dates(self) -> "GSTTaxRateCreate":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not be before effective_from")
        return self


class GSTTaxRateUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=255)
    effective_to: date | None = None
    is_active: bool | None = None


class GSTTaxRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    rate: Decimal
    description: str | None
    is_active: bool
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime
