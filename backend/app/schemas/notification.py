import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.compliance_enums import NotificationSeverity, NotificationType


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    severity: NotificationSeverity
    entity_type: str | None
    entity_id: uuid.UUID | None
    is_read: bool
    created_at: datetime
    read_at: datetime | None


class UnreadCount(BaseModel):
    unread_count: int
