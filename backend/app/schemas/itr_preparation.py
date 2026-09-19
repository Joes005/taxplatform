import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.income_tax_enums import ITRFormType, ITRPreparationStatus
from app.schemas.tax_computation import ValidationIssue


class ITRPreparationCreate(BaseModel):
    tax_computation_id: uuid.UUID


class ITRPreparationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    tax_computation_id: uuid.UUID
    itr_form_type: ITRFormType
    assessment_year: str
    status: ITRPreparationStatus
    prepared_by: uuid.UUID
    reviewed_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ITRValidationResult(BaseModel):
    preparation: ITRPreparationRead
    issues: list[ValidationIssue]
    has_errors: bool
