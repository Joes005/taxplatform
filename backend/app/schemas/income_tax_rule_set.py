import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.income_tax_enums import TaxpayerType, TaxRegime


class IncomeTaxSlabRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lower_limit: Decimal
    upper_limit: Decimal | None
    rate: Decimal
    order_index: int


class IncomeTaxRebateRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maximum_income: Decimal
    maximum_rebate: Decimal


class IncomeTaxSurchargeRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    income_threshold: Decimal
    rate: Decimal
    order_index: int


class IncomeTaxDeductionRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_code: str
    description: str
    max_amount: Decimal | None
    allowed_in_old_regime: bool
    allowed_in_new_regime: bool


class IncomeTaxRuleSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assessment_year: str
    taxpayer_type: TaxpayerType
    tax_regime: TaxRegime
    effective_from: date
    effective_to: date | None
    version: int
    is_active: bool
    cess_rate: Decimal
    description: str | None
    slabs: list[IncomeTaxSlabRead]
    rebate_rules: list[IncomeTaxRebateRuleRead]
    surcharge_rules: list[IncomeTaxSurchargeRuleRead]
    deduction_rules: list[IncomeTaxDeductionRuleRead]
