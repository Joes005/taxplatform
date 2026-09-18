import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.tds_enums import TDSReviewNoteStatus


class TDSReviewNoteCreate(BaseModel):
    return_period_id: uuid.UUID
    entity_type: str = Field(min_length=1, max_length=50)
    entity_id: str = Field(min_length=1, max_length=100)
    note: str = Field(min_length=1)


class TDSReviewNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    return_period_id: uuid.UUID
    entity_type: str
    entity_id: str
    note: str
    status: TDSReviewNoteStatus
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
