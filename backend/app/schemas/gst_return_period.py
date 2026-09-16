import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.gst_enums import GSTReturnPeriodStatus


class GSTReturnPeriodCreate(BaseModel):
    financial_year_id: uuid.UUID
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class GSTReturnPeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    year: int
    month: int
    period_start: date
    period_end: date
    status: GSTReturnPeriodStatus
    created_at: datetime
    updated_at: datetime
