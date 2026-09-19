import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.income_tax_enums import IncomeTaxSourceType


class IncomeTaxCreditEntryCreate(BaseModel):
    financial_year_id: uuid.UUID
    deductor_name: str = Field(min_length=1, max_length=255)
    deductor_tan: str | None = Field(default=None, max_length=10)
    section_code: str | None = Field(default=None, max_length=20)
    amount: Decimal
    certificate_reference: str | None = Field(default=None, max_length=100)
    source_type: IncomeTaxSourceType | None = None
    source_id: uuid.UUID | None = None


class IncomeTaxCreditEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    deductor_name: str
    deductor_tan: str | None
    section_code: str | None
    amount: Decimal
    certificate_reference: str | None
    source_type: IncomeTaxSourceType | None
    source_id: uuid.UUID | None
    created_by: uuid.UUID
