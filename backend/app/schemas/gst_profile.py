import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.gst_enums import GSTRegistrationType


class GSTProfileCreate(BaseModel):
    gstin: str = Field(min_length=15, max_length=15)
    legal_name: str = Field(min_length=1, max_length=255)
    trade_name: str | None = Field(default=None, max_length=255)
    registration_type: GSTRegistrationType = GSTRegistrationType.REGULAR
    registration_date: date | None = None


class GSTProfileUpdate(BaseModel):
    gstin: str | None = Field(default=None, min_length=15, max_length=15)
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    trade_name: str | None = Field(default=None, max_length=255)
    registration_type: GSTRegistrationType | None = None
    registration_date: date | None = None
    is_active: bool | None = None


class GSTProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    gstin: str
    legal_name: str
    trade_name: str | None
    registration_type: GSTRegistrationType
    state_code: str
    state_name: str
    registration_date: date | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
