import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.income_tax_enums import IncomeTaxSourceType


class IncomeTaxDeductionCreate(BaseModel):
    financial_year_id: uuid.UUID
    section_code: str = Field(min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=255)
    claimed_amount: Decimal = Decimal("0")
    source_type: IncomeTaxSourceType | None = None
    source_id: uuid.UUID | None = None


class IncomeTaxDeductionUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=255)
    claimed_amount: Decimal | None = None


class IncomeTaxDeductionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    section_code: str
    description: str | None
    claimed_amount: Decimal
    eligible_amount: Decimal
    source_type: IncomeTaxSourceType | None
    source_id: uuid.UUID | None
