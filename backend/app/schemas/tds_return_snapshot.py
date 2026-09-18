import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.tds_enums import TDSReturnSnapshotStatus, TDSReturnType


class TDSReturnSnapshotGenerateRequest(BaseModel):
    return_type: TDSReturnType = TDSReturnType.FORM_26Q


class TDSReturnSnapshotTransitionRequest(BaseModel):
    return_type: TDSReturnType = TDSReturnType.FORM_26Q
    comment: str | None = None


class TDSReturnSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    return_period_id: uuid.UUID
    return_type: TDSReturnType
    version: int
    status: TDSReturnSnapshotStatus
    generated_at: datetime
    generated_by: uuid.UUID | None
    summary_data: dict[str, Any]
