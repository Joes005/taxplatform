import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.tds_enums import PANStatus, TDSApplicabilityStatus, TDSTransactionStatus


class TDSTransactionCreate(BaseModel):
    deductee_id: uuid.UUID
    tds_section_id: uuid.UUID
    transaction_date: date
    gross_amount: Decimal = Field(gt=0)
    source_type: str | None = Field(default=None, max_length=20)
    source_id: uuid.UUID | None = None


class TDSTransactionUpdate(BaseModel):
    gross_amount: Decimal | None = Field(default=None, gt=0)
    transaction_date: date | None = None


class TDSTransactionOverride(BaseModel):
    tds_amount: Decimal = Field(ge=0)
    override_reason: str = Field(min_length=1, max_length=500)


class TDSTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    deductee_id: uuid.UUID
    tds_section_id: uuid.UUID
    tds_rule_id: uuid.UUID | None
    source_type: str | None
    source_id: uuid.UUID | None
    source: str
    source_reference: str | None
    transaction_date: date
    deduction_date: date | None
    gross_amount: Decimal
    taxable_amount: Decimal
    tds_rate: Decimal
    tds_amount: Decimal
    net_amount: Decimal
    pan_status: PANStatus
    applicability_status: TDSApplicabilityStatus | None
    applicability_reason: str | None
    system_calculated_amount: Decimal | None
    is_manual_override: bool
    override_reason: str | None
    overridden_by: uuid.UUID | None
    overridden_at: datetime | None
    status: TDSTransactionStatus
    created_at: datetime
    updated_at: datetime
