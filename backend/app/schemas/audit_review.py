import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit_workflow_enums import AuditReviewStatus, AuditReviewType, AuditSignOffType


class AuditReviewCreate(BaseModel):
    review_type: AuditReviewType


class AuditReviewCompleteRequest(BaseModel):
    summary: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)


class AuditReviewReturnRequest(BaseModel):
    notes: str = Field(min_length=1, max_length=5000)


class AuditReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    company_id: uuid.UUID
    reviewer_id: uuid.UUID
    review_type: AuditReviewType
    status: AuditReviewStatus
    summary: str | None
    notes: str | None
    started_at: datetime | None
    completed_at: datetime | None


class AuditSignOffCreate(BaseModel):
    sign_off_type: AuditSignOffType


class AuditSignOffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    company_id: uuid.UUID
    signed_by: uuid.UUID
    sign_off_type: AuditSignOffType
    statement: str
    created_at: datetime
