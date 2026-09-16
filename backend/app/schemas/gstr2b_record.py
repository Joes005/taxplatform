import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.gst_enums import GSTR2BDocumentType


class GSTR2BRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    return_period_id: uuid.UUID
    import_job_id: uuid.UUID | None
    supplier_gstin: str
    supplier_name: str | None
    invoice_number: str
    invoice_date: date
    document_type: GSTR2BDocumentType
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    source: str
    source_reference: str | None
    created_at: datetime
    updated_at: datetime
