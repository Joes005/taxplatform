import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.compliance_enums import (
    ComplianceCategory,
    ComplianceModule,
    CompliancePriority,
    ComplianceSourceType,
    ComplianceTaskStatus,
)


class ComplianceTaskCreate(BaseModel):
    obligation_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    category: ComplianceCategory
    module: ComplianceModule
    priority: CompliancePriority = CompliancePriority.MEDIUM
    assigned_to: uuid.UUID | None = None
    reviewer_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date
    source_type: ComplianceSourceType = ComplianceSourceType.MANUAL
    source_id: uuid.UUID | None = None


class ComplianceTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    priority: CompliancePriority | None = None
    start_date: date | None = None
    due_date: date | None = None


class ComplianceTaskAssignRequest(BaseModel):
    assigned_to: uuid.UUID | None = None
    reviewer_id: uuid.UUID | None = None


class ComplianceTaskCompleteRequest(BaseModel):
    completion_notes: str | None = Field(default=None, max_length=2000)


class ComplianceTaskReturnRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ComplianceTaskCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class ComplianceTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    obligation_id: uuid.UUID | None
    title: str
    description: str | None
    category: ComplianceCategory
    module: ComplianceModule
    status: ComplianceTaskStatus
    priority: CompliancePriority
    assigned_to: uuid.UUID | None
    reviewer_id: uuid.UUID | None
    start_date: date | None
    due_date: date
    completed_at: datetime | None
    verified_at: datetime | None
    source_type: ComplianceSourceType
    source_id: uuid.UUID | None
    completion_notes: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False


class ComplianceTaskCommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=3000)


class ComplianceTaskCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    comment: str
    created_at: datetime


class ComplianceTaskEvidenceCreate(BaseModel):
    document_id: uuid.UUID
    description: str | None = Field(default=None, max_length=500)


class ComplianceTaskEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    document_id: uuid.UUID
    description: str | None
    created_by: uuid.UUID
    created_at: datetime
