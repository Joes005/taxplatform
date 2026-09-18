import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.tds_enums import DeducteeType, PANStatus


class DeducteeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    vendor_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    pan: str | None = Field(default=None, max_length=10)
    deductee_type: DeducteeType = DeducteeType.OTHER
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    state: str | None = Field(default=None, max_length=100)
    state_code: str | None = Field(default=None, max_length=2)
    pincode: str | None = Field(default=None, max_length=10)


class DeducteeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    vendor_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    pan: str | None = Field(default=None, max_length=10)
    pan_status: PANStatus | None = None
    deductee_type: DeducteeType | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    state: str | None = Field(default=None, max_length=100)
    state_code: str | None = Field(default=None, max_length=2)
    pincode: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None


class DeducteeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    vendor_id: uuid.UUID | None
    customer_id: uuid.UUID | None
    name: str
    code: str | None
    pan: str | None
    pan_status: PANStatus
    deductee_type: DeducteeType
    email: str | None
    phone: str | None
    address: str | None
    state: str | None
    state_code: str | None
    pincode: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
