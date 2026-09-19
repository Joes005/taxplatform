import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.income_tax_enums import ResidentialStatus, TaxpayerType


class IncomeTaxProfileCreate(BaseModel):
    pan: str = Field(min_length=10, max_length=10)
    legal_name: str = Field(min_length=1, max_length=255)
    trade_name: str | None = Field(default=None, max_length=255)
    taxpayer_type: TaxpayerType = TaxpayerType.COMPANY
    residential_status: ResidentialStatus = ResidentialStatus.RESIDENT
    date_of_birth_or_incorporation: date | None = None
    business_nature: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=10)


class IncomeTaxProfileUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    trade_name: str | None = Field(default=None, max_length=255)
    taxpayer_type: TaxpayerType | None = None
    residential_status: ResidentialStatus | None = None
    date_of_birth_or_incorporation: date | None = None
    business_nature: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=10)


class IncomeTaxProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    pan: str
    legal_name: str
    trade_name: str | None
    taxpayer_type: TaxpayerType
    residential_status: ResidentialStatus
    date_of_birth_or_incorporation: date | None
    business_nature: str | None
    address: str | None
    city: str | None
    state: str | None
    pincode: str | None
    created_at: datetime
    updated_at: datetime
