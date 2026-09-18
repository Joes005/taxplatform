import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.audit_workflow_enums import AuditEngagementStatus, AuditEngagementType


class AuditEngagementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    financial_year_id: uuid.UUID
    period_start: date
    period_end: date
    engagement_type: AuditEngagementType = AuditEngagementType.INTERNAL_REVIEW

    @model_validator(mode="after")
    def check_dates(self) -> "AuditEngagementCreate":
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        return self


class AuditEngagementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    engagement_type: AuditEngagementType | None = None


class AuditEngagementActionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)


class AuditEngagementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    engagement_code: str
    title: str
    description: str | None
    financial_year_id: uuid.UUID
    period_start: date
    period_end: date
    engagement_type: AuditEngagementType
    status: AuditEngagementStatus
    is_locked: bool
    locked_at: datetime | None
    locked_by: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
