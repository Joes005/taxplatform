import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.accounting_enums import PeriodStatus


class AccountingPeriodCreate(BaseModel):
    financial_year_id: uuid.UUID
    name: str = Field(min_length=1, max_length=50)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def check_dates(self) -> "AccountingPeriodCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class AccountingPeriodUpdate(BaseModel):
    status: PeriodStatus | None = None


class AccountingPeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_year_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    status: PeriodStatus
    created_at: datetime
    updated_at: datetime
