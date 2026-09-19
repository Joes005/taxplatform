import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.income_tax_enums import IncomeTaxSourceType, TaxAdjustmentType


class IncomeTaxAdjustmentCreate(BaseModel):
    financial_year_id: uuid.UUID
    adjustment_type: TaxAdjustmentType
    description: str = Field(min_length=1, max_length=500)
    book_amount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    source_type: IncomeTaxSourceType | None = None
    source_id: uuid.UUID | None = None


class IncomeTaxAdjustmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    adjustment_type: TaxAdjustmentType
    description: str
    book_amount: Decimal
    tax_amount: Decimal
    difference: Decimal
    source_type: IncomeTaxSourceType | None
    source_id: uuid.UUID | None
    created_by: uuid.UUID
