import uuid
from datetime import date, datetime
from typing import Any

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
    assigned_to: uuid.UUID | None = None
    reviewer_id: uuid.UUID | None = None
    prerequisite_config: dict[str, Any] | None = None


class ComplianceObligationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    grace_date: date | None = None
    priority: CompliancePriority | None = None
    status: ComplianceObligationStatus | None = None
    active: bool | None = None
    assigned_to: uuid.UUID | None = None
    reviewer_id: uuid.UUID | None = None
    review_notes: str | None = None
    prerequisite_config: dict[str, Any] | None = None


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
    assigned_to: uuid.UUID | None = None
    reviewer_id: uuid.UUID | None = None
    readiness_status: str = "NOT_APPLICABLE"
    readiness_details: dict[str, Any] | None = None
    completed_at: datetime | None = None
    approved_at: datetime | None = None
    review_notes: str | None = None
    prerequisite_config: dict[str, Any] | None = None
    is_overdue: bool = False
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class GenerateTaskRequest(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    assigned_to: uuid.UUID | None = None
    reviewer_id: uuid.UUID | None = None


class ObligationAssignRequest(BaseModel):
    assigned_to: uuid.UUID | None = None
    reviewer_id: uuid.UUID | None = None


class ObligationReviewActionRequest(BaseModel):
    review_notes: str | None = Field(default=None, max_length=2000)


class ObligationReopenRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ObligationEvidenceCreate(BaseModel):
    document_id: uuid.UUID
    description: str | None = Field(default=None, max_length=500)


class ObligationEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    obligation_id: uuid.UUID
    company_id: uuid.UUID
    document_id: uuid.UUID
    description: str | None
    created_by: uuid.UUID
    created_at: datetime


class ReadinessCheckItemRead(BaseModel):
    check_code: str
    description: str
    status: str
    blocking: bool
    source_module: str
    entity_reference: str | None = None
    remediation_action: str = ""
    deep_link: str = ""


class ReadinessResultRead(BaseModel):
    obligation_id: uuid.UUID
    overall_status: str
    checks: list[ReadinessCheckItemRead]
    checked_at: datetime
    blocking_issues_count: int


class ComplianceHealthRead(BaseModel):
    health_status: str
    score: int
    summary: str
    reasons: list[str]
    dimensions: dict[str, int]


class ComplianceControlCenterSummaryRead(BaseModel):
    total_obligations: int
    due_soon: int
    overdue: int
    blocked: int
    awaiting_review: int
    completed: int
    health: ComplianceHealthRead
