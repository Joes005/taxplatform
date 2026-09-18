import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit_workflow_enums import (
    AuditFindingCategory,
    AuditFindingSeverity,
    AuditFindingSourceType,
    AuditFindingStatus,
)


class AuditFindingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    category: AuditFindingCategory
    severity: AuditFindingSeverity
    source_type: AuditFindingSourceType | None = None
    source_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    due_date: date | None = None


class AuditFindingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    category: AuditFindingCategory | None = None
    severity: AuditFindingSeverity | None = None
    due_date: date | None = None


class AuditFindingAssignRequest(BaseModel):
    assigned_to: uuid.UUID


class AuditFindingResolveRequest(BaseModel):
    resolution_summary: str = Field(min_length=1, max_length=5000)


class AuditFindingReopenRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class AuditFindingRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class AuditFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    company_id: uuid.UUID
    finding_code: str
    title: str
    description: str | None
    category: AuditFindingCategory
    severity: AuditFindingSeverity
    status: AuditFindingStatus
    source_type: AuditFindingSourceType | None
    source_id: uuid.UUID | None
    assigned_to: uuid.UUID | None
    created_by: uuid.UUID
    due_date: date | None
    resolution_summary: str | None
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AuditFindingCreateResult(BaseModel):
    finding: AuditFindingRead
    duplicate_warning: bool
    duplicate_finding_codes: list[str] = Field(default_factory=list)


class AuditFindingCommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=3000)


class AuditFindingCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    user_id: uuid.UUID
    comment: str
    created_at: datetime


class AuditFindingEvidenceCreate(BaseModel):
    document_id: uuid.UUID
    description: str | None = Field(default=None, max_length=500)


class AuditFindingEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    document_id: uuid.UUID
    description: str | None
    added_by: uuid.UUID
    added_at: datetime


class AuditFindingResponseCreate(BaseModel):
    response_text: str = Field(min_length=1, max_length=5000)


class AuditFindingResponseReviewRequest(BaseModel):
    accept: bool
    review_comment: str | None = Field(default=None, max_length=2000)


class AuditFindingResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    submitted_by: uuid.UUID
    response_text: str
    submitted_at: datetime
    status: str
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_comment: str | None
