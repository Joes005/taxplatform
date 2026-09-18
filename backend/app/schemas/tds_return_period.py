import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.tds_enums import TDSQuarter, TDSReturnPeriodStatus


class TDSReturnPeriodCreate(BaseModel):
    financial_year_id: uuid.UUID
    quarter: TDSQuarter


class TDSReturnPeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    quarter: TDSQuarter
    period_start: date
    period_end: date
    status: TDSReturnPeriodStatus
    created_at: datetime
    updated_at: datetime
