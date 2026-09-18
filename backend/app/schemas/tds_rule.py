import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.tds_enums import DeducteeType, TDSRateType


class TDSRuleCreate(BaseModel):
    tds_section_id: uuid.UUID
    rate: Decimal = Field(ge=0, le=100)
    rate_type: TDSRateType = TDSRateType.PERCENTAGE
    no_pan_rate: Decimal | None = Field(default=None, ge=0, le=100)
    threshold_amount: Decimal = Field(default=Decimal("0"), ge=0)
    aggregate_threshold_amount: Decimal | None = Field(default=None, ge=0)
    deductee_type: DeducteeType | None = None
    pan_required: bool = False
    effective_from: date
    effective_to: date | None = None
    special_condition: str | None = Field(default=None, max_length=500)
    is_active: bool = True

    @model_validator(mode="after")
    def check_dates(self) -> "TDSRuleCreate":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not be before effective_from")
        return self


class TDSRuleUpdate(BaseModel):
    rate: Decimal | None = Field(default=None, ge=0, le=100)
    no_pan_rate: Decimal | None = Field(default=None, ge=0, le=100)
    threshold_amount: Decimal | None = Field(default=None, ge=0)
    aggregate_threshold_amount: Decimal | None = Field(default=None, ge=0)
    pan_required: bool | None = None
    effective_to: date | None = None
    special_condition: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class TDSRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tds_section_id: uuid.UUID
    company_id: uuid.UUID | None
    rate: Decimal
    rate_type: TDSRateType
    no_pan_rate: Decimal | None
    threshold_amount: Decimal
    aggregate_threshold_amount: Decimal | None
    deductee_type: DeducteeType | None
    pan_required: bool
    effective_from: date
    effective_to: date | None
    special_condition: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
