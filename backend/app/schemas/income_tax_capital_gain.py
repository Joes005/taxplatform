import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.income_tax_enums import CapitalAssetType, CapitalGainType


class IncomeTaxCapitalGainCreate(BaseModel):
    financial_year_id: uuid.UUID
    asset_type: CapitalAssetType
    asset_description: str = Field(min_length=1, max_length=500)
    purchase_date: date
    sale_date: date
    purchase_cost: Decimal = Decimal("0")
    improvement_cost: Decimal = Decimal("0")
    sale_consideration: Decimal = Decimal("0")
    transfer_expenses: Decimal = Decimal("0")
    indexed_cost: Decimal | None = None
    gain_type: CapitalGainType


class IncomeTaxCapitalGainUpdate(BaseModel):
    asset_description: str | None = Field(default=None, min_length=1, max_length=500)
    purchase_cost: Decimal | None = None
    improvement_cost: Decimal | None = None
    sale_consideration: Decimal | None = None
    transfer_expenses: Decimal | None = None
    indexed_cost: Decimal | None = None
    gain_type: CapitalGainType | None = None


class IncomeTaxCapitalGainRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    asset_type: CapitalAssetType
    asset_description: str
    purchase_date: date
    sale_date: date
    purchase_cost: Decimal
    improvement_cost: Decimal
    sale_consideration: Decimal
    transfer_expenses: Decimal
    indexed_cost: Decimal | None
    gain_type: CapitalGainType
    gain_amount: Decimal
