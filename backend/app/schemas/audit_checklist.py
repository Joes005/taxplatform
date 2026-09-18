import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit_workflow_enums import AuditChecklistCategory, AuditChecklistItemStatus


class AuditChecklistItemCreate(BaseModel):
    category: AuditChecklistCategory
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    order_index: int = 0


class AuditChecklistItemUpdate(BaseModel):
    status: AuditChecklistItemStatus | None = None
    assigned_to: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class AuditChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    checklist_id: uuid.UUID
    engagement_id: uuid.UUID
    company_id: uuid.UUID
    category: AuditChecklistCategory
    title: str
    description: str | None
    order_index: int
    status: AuditChecklistItemStatus
    assigned_to: uuid.UUID | None
    completed_by: uuid.UUID | None
    completed_at: datetime | None
    notes: str | None


class AuditChecklistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    company_id: uuid.UUID
    name: str
    items: list[AuditChecklistItemRead]
