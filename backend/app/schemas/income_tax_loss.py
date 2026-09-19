import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.income_tax_enums import TaxLossType


class IncomeTaxLossCreate(BaseModel):
    origin_financial_year_id: uuid.UUID
    loss_type: TaxLossType
    amount: Decimal


class IncomeTaxLossRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    origin_financial_year_id: uuid.UUID
    loss_type: TaxLossType
    amount: Decimal
    setoff_amount: Decimal
    carried_forward_amount: Decimal
    expiry_financial_year_id: uuid.UUID | None
    created_by: uuid.UUID
