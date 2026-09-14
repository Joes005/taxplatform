import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.document import DocumentStatus, DocumentType


class DocumentUploaderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str


class DocumentUpdate(BaseModel):
    document_type: DocumentType | None = None
    description: Annotated[str | None, Field(default=None, max_length=1000)] = None


class DocumentRead(BaseModel):
    """Metadata only — `storage_path` (the internal storage key) is
    intentionally never exposed to API clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    document_type: DocumentType
    status: DocumentStatus
    mime_type: str
    file_extension: str
    file_size: int
    checksum: str
    description: str | None
    uploaded_by: DocumentUploaderSummary
    uploaded_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    @computed_field
    @property
    def is_archived(self) -> bool:
        return self.status == DocumentStatus.ARCHIVED
