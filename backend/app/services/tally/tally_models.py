from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


class TallyFormat(StrEnum):
    TALLY_XML = "TALLY_XML"
    XML = "XML"
    CSV = "CSV"
    XLSX = "XLSX"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"


class TallyVoucherType(StrEnum):
    SALES = "SALES"
    PURCHASE = "PURCHASE"
    RECEIPT = "RECEIPT"
    PAYMENT = "PAYMENT"
    JOURNAL = "JOURNAL"
    CONTRA = "CONTRA"
    CREDIT_NOTE = "CREDIT_NOTE"
    DEBIT_NOTE = "DEBIT_NOTE"
    OTHER = "OTHER"


class MappingStatus(StrEnum):
    AUTO_MAPPED = "AUTO_MAPPED"
    MANUALLY_MAPPED = "MANUALLY_MAPPED"
    NEW = "NEW"
    AMBIGUOUS = "AMBIGUOUS"
    INVALID = "INVALID"
    SKIPPED = "SKIPPED"


class ValidationSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class TallyCompanyRecord(BaseModel):
    name: str = ""
    books_from: date | None = None
    financial_year: str | None = None
    gstin: str | None = None
    pan: str | None = None
    state: str | None = None
    address: str | None = None


class TallyGroupRecord(BaseModel):
    name: str
    parent: str | None = None
    is_revenue: bool | None = None
    is_deemed_positive: bool | None = None


class TallyLedgerRecord(BaseModel):
    name: str
    parent_group: str | None = None
    opening_balance: Decimal = Decimal(0)
    is_debit: bool = True
    closing_balance: Decimal | None = None
    gstin: str | None = None
    pan: str | None = None
    state: str | None = None
    address: str | None = None
    ledger_type: str | None = None
    tax_rate: Decimal | None = None


class TallyPartyRecord(BaseModel):
    name: str
    party_type: str = "CUSTOMER"  # CUSTOMER, VENDOR, or BOTH
    gstin: str | None = None
    pan: str | None = None
    state: str | None = None
    state_code: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    opening_balance: Decimal = Decimal(0)
    is_debit: bool = True


class TallyStockItemRecord(BaseModel):
    name: str
    parent_group: str | None = None
    unit: str | None = None
    hsn_sac: str | None = None
    tax_rate: Decimal | None = None
    opening_qty: Decimal | None = None
    opening_val: Decimal | None = None


class TallyInventoryLine(BaseModel):
    item_name: str
    quantity: Decimal = Decimal(1)
    rate: Decimal = Decimal(0)
    amount: Decimal = Decimal(0)
    unit: str | None = None
    hsn_sac: str | None = None
    tax_rate: Decimal | None = None


class TallyVoucherLine(BaseModel):
    ledger_name: str
    amount: Decimal = Decimal(0)
    is_debit: bool = True
    narration: str | None = None
    inventory_items: list[TallyInventoryLine] = Field(default_factory=list)


class TallyTaxBreakdown(BaseModel):
    taxable_amount: Decimal = Decimal(0)
    cgst_amount: Decimal = Decimal(0)
    sgst_amount: Decimal = Decimal(0)
    igst_amount: Decimal = Decimal(0)
    cess_amount: Decimal = Decimal(0)
    total_tax: Decimal = Decimal(0)


class TallyVoucherRecord(BaseModel):
    voucher_type: str  # Original Tally string, e.g. "Sales"
    normalized_type: TallyVoucherType = TallyVoucherType.OTHER
    voucher_number: str
    voucher_date: date
    party_name: str | None = None
    reference_no: str | None = None
    reference_date: date | None = None
    narration: str | None = None
    lines: list[TallyVoucherLine] = Field(default_factory=list)
    inventory: list[TallyInventoryLine] = Field(default_factory=list)
    total_amount: Decimal = Decimal(0)
    tax_breakdown: TallyTaxBreakdown = Field(default_factory=TallyTaxBreakdown)
    fingerprint: str = ""
    # TDS specific
    tds_section: str | None = None
    tds_rate: Decimal | None = None
    tds_amount: Decimal | None = None


class TallyOpeningBalanceRecord(BaseModel):
    ledger_name: str
    amount: Decimal = Decimal(0)
    is_debit: bool = True
    financial_year: str | None = None


class TallyValidationError(BaseModel):
    code: str
    message: str
    entity: str
    row_ref: str | int
    field: str | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    extra: dict[str, Any] | None = None


class TallyMappingRule(BaseModel):
    source_type: str  # LEDGER, PARTY, PRODUCT, VOUCHER_TYPE
    source_name: str
    target_id: str | None = None
    target_name: str | None = None
    status: MappingStatus = MappingStatus.NEW
    confidence: float = 1.0
    notes: str | None = None


class TallyImportBatch(BaseModel):
    company_id: str
    detected_format: TallyFormat
    company_record: TallyCompanyRecord | None = None
    groups: list[TallyGroupRecord] = Field(default_factory=list)
    ledgers: list[TallyLedgerRecord] = Field(default_factory=list)
    parties: list[TallyPartyRecord] = Field(default_factory=list)
    stock_items: list[TallyStockItemRecord] = Field(default_factory=list)
    vouchers: list[TallyVoucherRecord] = Field(default_factory=list)
    opening_balances: list[TallyOpeningBalanceRecord] = Field(default_factory=list)
    raw_record_count: int = 0


class TallyReconciliationItem(BaseModel):
    entity_type: str
    source_count: int = 0
    source_amount: Decimal = Decimal(0)
    imported_count: int = 0
    imported_amount: Decimal = Decimal(0)
    difference_count: int = 0
    difference_amount: Decimal = Decimal(0)
    is_matched: bool = True
    notes: str | None = None


class TallyReconciliationReport(BaseModel):
    company_id: str
    import_job_id: str | None = None
    reconciled_at: datetime = Field(default_factory=datetime.utcnow)
    items: list[TallyReconciliationItem] = Field(default_factory=list)
    overall_matched: bool = True
    source_total: Decimal = Decimal(0)
    imported_total: Decimal = Decimal(0)
    total_difference: Decimal = Decimal(0)
