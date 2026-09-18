import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TDSSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    section_code: str
    name: str
    description: str | None
    payment_nature: str | None
    is_active: bool
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime
