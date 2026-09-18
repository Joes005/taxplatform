import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.audit_workflow_enums import AuditAssignmentRole


class AuditAssignmentCreate(BaseModel):
    user_id: uuid.UUID
    role: AuditAssignmentRole


class AuditAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    role: AuditAssignmentRole
    assigned_by: uuid.UUID
    assigned_at: datetime
    unassigned_at: datetime | None
    is_active: bool
