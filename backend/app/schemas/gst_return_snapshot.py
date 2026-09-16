import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.gst_enums import GSTReturnSnapshotStatus, GSTReturnType


class GSTReturnSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    return_period_id: uuid.UUID
    return_type: GSTReturnType
    version: int
    status: GSTReturnSnapshotStatus
    generated_at: datetime
    generated_by: uuid.UUID | None
    summary_data: dict[str, Any]


class GSTReturnSnapshotGenerateRequest(BaseModel):
    return_type: GSTReturnType


class GSTReturnSnapshotTransitionRequest(BaseModel):
    return_type: GSTReturnType
    comment: str | None = Field(default=None, max_length=500)
