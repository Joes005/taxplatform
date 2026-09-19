import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.compliance_enums import (
    ComplianceCategory,
    ComplianceFrequency,
    ComplianceModule,
    ComplianceObligationStatus,
    CompliancePriority,
)


class ComplianceObligationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: ComplianceCategory
    module: ComplianceModule
    frequency: ComplianceFrequency
    financial_year_id: uuid.UUID | None = None
    tax_period: str | None = Field(default=None, max_length=20)
    start_date: date
    due_date: date
    grace_date: date | None = None
    priority: CompliancePriority = CompliancePriority.MEDIUM


class ComplianceObligationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    grace_date: date | None = None
    priority: CompliancePriority | None = None
    status: ComplianceObligationStatus | None = None
    active: bool | None = None


class ComplianceObligationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
    description: str | None
    category: ComplianceCategory
    module: ComplianceModule
    frequency: ComplianceFrequency
    financial_year_id: uuid.UUID | None
    tax_period: str | None
    start_date: date
    due_date: date
    grace_date: date | None
    priority: CompliancePriority
    status: ComplianceObligationStatus
    is_recurring: bool
    rule_id: uuid.UUID | None
    rule_version: int | None
    source_reference: str | None
    active: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class GenerateTaskRequest(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    assigned_to: uuid.UUID | None = None
    reviewer_id: uuid.UUID | None = None
