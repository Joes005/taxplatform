import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.income_tax_enums import TaxComputationStatus, TaxRegime


class TaxComputationCreate(BaseModel):
    financial_year_id: uuid.UUID
    tax_regime: TaxRegime


class TaxComputationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    assessment_year: str
    tax_regime: TaxRegime
    rule_set_id: uuid.UUID | None
    status: TaxComputationStatus

    salary_income: Decimal
    house_property_income: Decimal
    business_income: Decimal
    capital_gains_income: Decimal
    other_income: Decimal
    gross_total_income: Decimal

    total_deductions: Decimal
    taxable_income: Decimal

    tax_before_rebate: Decimal
    rebate: Decimal
    tax_after_rebate: Decimal
    surcharge: Decimal
    cess: Decimal
    gross_tax_liability: Decimal

    tds_credit_total: Decimal
    advance_tax_total: Decimal
    self_assessment_tax_total: Decimal
    balance_payable_or_refund: Decimal

    calculated_at: datetime | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TaxComputationSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_computation_id: uuid.UUID
    rule_set_id: uuid.UUID | None
    version: int
    generated_at: datetime
    generated_by: uuid.UUID | None
    summary_data: dict[str, Any]


class ValidationIssue(BaseModel):
    severity: str
    code: str
    message: str
    field: str | None = None
