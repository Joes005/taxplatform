import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.accounting_enums import ItemType


class ProductServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    item_type: ItemType
    description: str | None = Field(default=None, max_length=1000)
    hsn_sac: str | None = Field(default=None, max_length=20)
    unit: str | None = Field(default=None, max_length=20)
    tax_rate: Decimal = Decimal("0")


class ProductServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    item_type: ItemType | None = None
    description: str | None = Field(default=None, max_length=1000)
    hsn_sac: str | None = Field(default=None, max_length=20)
    unit: str | None = Field(default=None, max_length=20)
    tax_rate: Decimal | None = None
    is_active: bool | None = None


class ProductServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str | None
    item_type: ItemType
    description: str | None
    hsn_sac: str | None
    unit: str | None
    tax_rate: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
