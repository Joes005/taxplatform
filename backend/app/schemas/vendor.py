import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.gst_validators import is_valid_gstin_format


def _validate_gstin(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    value = value.strip().upper()
    if not is_valid_gstin_format(value):
        raise ValueError("GSTIN does not match the expected 15-character structure")
    return value


class VendorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    gstin: str | None = None
    pan: str | None = Field(default=None, max_length=10)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    state: str | None = Field(default=None, max_length=100)
    state_code: str | None = Field(default=None, max_length=2)
    pincode: str | None = Field(default=None, max_length=10)

    @field_validator("gstin")
    @classmethod
    def check_gstin(cls, value: str | None) -> str | None:
        return _validate_gstin(value)


class VendorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    gstin: str | None = None
    pan: str | None = Field(default=None, max_length=10)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    state: str | None = Field(default=None, max_length=100)
    state_code: str | None = Field(default=None, max_length=2)
    pincode: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None

    @field_validator("gstin")
    @classmethod
    def check_gstin(cls, value: str | None) -> str | None:
        return _validate_gstin(value)


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str | None
    gstin: str | None
    pan: str | None
    email: str | None
    phone: str | None
    address: str | None
    state: str | None
    state_code: str | None
    pincode: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
