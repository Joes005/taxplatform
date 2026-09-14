import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    user_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    description: str | None
    ip_address: str | None
    user_agent: str | None
    log_metadata: dict[str, Any] | None
    created_at: datetime
