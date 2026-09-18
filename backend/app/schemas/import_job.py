import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.accounting_enums import ImportStatus, ImportType


class ImportJobCreate(BaseModel):
    document_id: uuid.UUID
    import_type: ImportType
    financial_year_id: uuid.UUID | None = None
    return_period_id: uuid.UUID | None = Field(
        default=None, description="Required when import_type is GSTR2B"
    )
    bank_statement_id: uuid.UUID | None = Field(
        default=None, description="Required when import_type is BANK_STATEMENT"
    )
    column_mapping: dict[str, str] = Field(
        description="Maps each source file column name to a system field name"
    )


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    financial_year_id: uuid.UUID | None
    return_period_id: uuid.UUID | None
    bank_statement_id: uuid.UUID | None
    import_type: ImportType
    status: ImportStatus
    column_mapping: dict | None
    total_rows: int
    successful_rows: int
    failed_rows: int
    duplicate_rows: int
    created_at: datetime
    completed_at: datetime | None
    created_by: uuid.UUID


class ImportRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    row_number: int
    raw_data: dict
    normalized_data: dict | None
    status: str
    created_record_id: uuid.UUID | None


class ImportErrorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    row_number: int
    field_name: str | None
    error_code: str
    error_message: str
    raw_value: str | None
    created_at: datetime


class FieldDefinitionRead(BaseModel):
    name: str
    label: str
    required: bool


class ImportColumnPreview(BaseModel):
    columns: list[str]
    sample_rows: list[dict]
