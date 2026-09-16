import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.gst_common import GSTValidationFinding


class GSTR1B2BRow(BaseModel):
    sales_invoice_id: uuid.UUID
    recipient_gstin: str
    recipient_name: str
    invoice_number: str
    invoice_date: date
    invoice_value: Decimal
    place_of_supply_state_code: str | None
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal


class GSTR1B2CLargeRow(BaseModel):
    sales_invoice_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    invoice_value: Decimal
    place_of_supply_state_code: str | None
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal


class GSTR1B2COthersRow(BaseModel):
    place_of_supply_state_code: str | None
    tax_rate: Decimal
    invoice_count: int
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal


class GSTR1NoteRow(BaseModel):
    note_id: uuid.UUID
    note_number: str
    note_date: date
    reference_invoice_id: uuid.UUID | None
    reference_invoice_number: str | None
    recipient_gstin: str | None
    recipient_name: str | None
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal


class GSTR1HSNRow(BaseModel):
    hsn_sac: str | None
    description: str | None
    uqc: str | None
    tax_rate: Decimal
    quantity: Decimal
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_value: Decimal


class GSTR1DocumentSummaryRow(BaseModel):
    document_type: str
    total_count: int
    cancelled_count: int
    net_count: int


class GSTR1Overview(BaseModel):
    return_period_id: uuid.UUID
    b2b_invoice_count: int
    b2c_large_invoice_count: int
    b2c_others_invoice_count: int
    export_count: int
    credit_note_count: int
    debit_note_count: int
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    error_count: int
    warning_count: int


class GSTR1ValidationResponse(BaseModel):
    findings: list[GSTValidationFinding]
    error_count: int
    warning_count: int
