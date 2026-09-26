from datetime import date, datetime
from decimal import Decimal
from typing import Any
import uuid
from pydantic import BaseModel, Field

from app.services.tally.tally_models import (
    MappingStatus,
    TallyFormat,
    TallyMappingRule,
    TallyReconciliationReport,
    TallyValidationError,
    ValidationSeverity,
)


class TallyDetectResponse(BaseModel):
    format: TallyFormat
    detected_encoding: str
    file_size: int
    is_valid: bool
    error_message: str | None = None
    has_tally_markers: bool = False


class TallyPreviewRequest(BaseModel):
    document_id: uuid.UUID
    financial_year_id: uuid.UUID | None = None
    template_id: uuid.UUID | None = None
    manual_mappings: dict[str, str] | None = None


class TallyRowPreview(BaseModel):
    row_number: int
    voucher_type: str
    voucher_number: str
    voucher_date: str
    party_name: str
    total_amount: float
    status: str
    is_duplicate: bool
    narration: str | None = None


class TallyPreviewResponse(BaseModel):
    job_id: uuid.UUID
    format: str
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    warnings_count: int
    review_required_count: int
    can_commit: bool
    mappings: list[TallyMappingRule]
    errors: list[TallyValidationError]
    rows: list[TallyRowPreview]


class TallyCommitRequest(BaseModel):
    job_id: uuid.UUID
    financial_year_id: uuid.UUID | None = None
    confirmed_mappings: list[TallyMappingRule] | None = None
    save_as_template_name: str | None = None


class TallyCommitResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    reconciliation: TallyReconciliationReport
    message: str


class TallyMappingTemplateCreate(BaseModel):
    name: str
    rules: dict[str, Any]


class TallyMappingTemplateUpdate(BaseModel):
    name: str | None = None
    rules: dict[str, Any] | None = None


class TallyMappingTemplateRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    version: int
    rules: dict[str, Any]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TallyExportRequest(BaseModel):
    financial_year_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    voucher_types: list[str] = Field(default_factory=lambda: ["SALES", "PURCHASE", "RECEIPT", "PAYMENT", "JOURNAL"])
    format: str = "XML"  # XML, CSV, XLSX


class TallyExportPreviewResponse(BaseModel):
    total_vouchers: int
    total_amount: float
    total_ledgers: int
    by_type: dict[str, dict[str, Any]]
