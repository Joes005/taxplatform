import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.accounting_enums import FinancialYearStatus


class FinancialYearCreate(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    start_date: date
    end_date: date
    is_current: bool = False

    @model_validator(mode="after")
    def check_dates(self) -> "FinancialYearCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class FinancialYearUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    is_current: bool | None = None
    status: FinancialYearStatus | None = None


class FinancialYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_current: bool
    status: FinancialYearStatus
    created_at: datetime
    updated_at: datetime
