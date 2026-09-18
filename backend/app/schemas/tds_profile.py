import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.tds_enums import DeductorType, TDSProfileStatus


class TDSProfileCreate(BaseModel):
    tan: str = Field(min_length=10, max_length=10)
    pan: str = Field(min_length=10, max_length=10)
    legal_name: str = Field(min_length=1, max_length=255)
    trade_name: str | None = Field(default=None, max_length=255)
    deductor_type: DeductorType = DeductorType.COMPANY
    state_code: str | None = Field(default=None, max_length=2)
    state_name: str | None = Field(default=None, max_length=100)


class TDSProfileUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    trade_name: str | None = Field(default=None, max_length=255)
    deductor_type: DeductorType | None = None
    state_code: str | None = Field(default=None, max_length=2)
    state_name: str | None = Field(default=None, max_length=100)
    status: TDSProfileStatus | None = None


class TDSProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    tan: str
    pan: str
    legal_name: str
    trade_name: str | None
    deductor_type: DeductorType
    state_code: str | None
    state_name: str | None
    status: TDSProfileStatus
    created_at: datetime
    updated_at: datetime
