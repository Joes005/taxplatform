"""§26 — per-import-type row validation. Each validator turns one mapped
row into a normalized dict ready for record creation, or a list of
(field, error_code, message) problems. Nothing here writes to the
database — ImportService.commit() is the only place staged rows become
real records, after every row has already been validated.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_enums import ImportType
from app.models.customer import Customer
from app.models.deductee import Deductee
from app.models.ledger import Ledger
from app.models.tds_section import TDSSection
from app.models.vendor import Vendor
from app.services.imports.normalizers import (
    NormalizationError,
    normalize_amount,
    normalize_date,
    normalize_optional_amount,
    normalize_text,
)


@dataclass
class RowError:
    field_name: str | None
    error_code: str
    error_message: str


@dataclass
class RowResult:
    normalized: dict | None = None
    errors: list[RowError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.normalized is not None and not self.errors


class ImportContext:
    """Preloads company lookups once per job (name -> id) instead of
    re-querying per row — an import can be thousands of rows, and an N+1
    customer lookup would make that unusably slow.
    """

    def __init__(self, db: AsyncSession, company_id: uuid.UUID) -> None:
        self.db = db
        self.company_id = company_id
        self.customers_by_name: dict[str, uuid.UUID] = {}
        self.vendors_by_name: dict[str, uuid.UUID] = {}
        self.ledgers_by_name: dict[str, uuid.UUID] = {}
        self.deductees_by_name: dict[str, uuid.UUID] = {}
        self.tds_sections_by_code: dict[str, uuid.UUID] = {}

    async def load(self) -> None:
        customers = await self.db.execute(
            select(Customer.id, Customer.name).where(Customer.company_id == self.company_id)
        )
        self.customers_by_name = {name.strip().lower(): id_ for id_, name in customers}

        vendors = await self.db.execute(
            select(Vendor.id, Vendor.name).where(Vendor.company_id == self.company_id)
        )
        self.vendors_by_name = {name.strip().lower(): id_ for id_, name in vendors}

        ledgers = await self.db.execute(
            select(Ledger.id, Ledger.name).where(Ledger.company_id == self.company_id)
        )
        self.ledgers_by_name = {name.strip().lower(): id_ for id_, name in ledgers}

        deductees = await self.db.execute(
            select(Deductee.id, Deductee.name).where(Deductee.company_id == self.company_id)
        )
        self.deductees_by_name = {name.strip().lower(): id_ for id_, name in deductees}

        sections = await self.db.execute(select(TDSSection.id, TDSSection.section_code))
        self.tds_sections_by_code = {code.strip().upper(): id_ for id_, code in sections}


def _require(row: dict, field_name: str) -> str | None:
    value = row.get(field_name)
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return str(value).strip()


def validate_customer_row(row: dict, ctx: ImportContext) -> RowResult:
    result = RowResult()
    name = _require(row, "name")
    if not name:
        result.errors.append(RowError("name", "MISSING_REQUIRED_FIELD", "Customer name is required"))
        return result

    normalized = {
        "name": name,
        "code": normalize_text(row.get("code")),
        "gstin": normalize_text(row.get("gstin")),
        "pan": normalize_text(row.get("pan")),
        "email": normalize_text(row.get("email")),
        "phone": normalize_text(row.get("phone")),
        "billing_address": normalize_text(row.get("billing_address")),
        "state": normalize_text(row.get("state")),
        "state_code": normalize_text(row.get("state_code")),
        "pincode": normalize_text(row.get("pincode")),
    }
    if normalized["gstin"]:
        from app.utils.gst_validators import is_valid_gstin_format

        if not is_valid_gstin_format(normalized["gstin"]):
            result.errors.append(RowError("gstin", "INVALID_GSTIN", f"'{normalized['gstin']}' is not a valid GSTIN"))
            return result

    result.normalized = normalized
    return result


def validate_vendor_row(row: dict, ctx: ImportContext) -> RowResult:
    result = RowResult()
    name = _require(row, "name")
    if not name:
        result.errors.append(RowError("name", "MISSING_REQUIRED_FIELD", "Vendor name is required"))
        return result

    normalized = {
        "name": name,
        "code": normalize_text(row.get("code")),
        "gstin": normalize_text(row.get("gstin")),
        "pan": normalize_text(row.get("pan")),
        "email": normalize_text(row.get("email")),
        "phone": normalize_text(row.get("phone")),
        "address": normalize_text(row.get("address")),
        "state": normalize_text(row.get("state")),
        "state_code": normalize_text(row.get("state_code")),
        "pincode": normalize_text(row.get("pincode")),
    }
    if normalized["gstin"]:
        from app.utils.gst_validators import is_valid_gstin_format

        if not is_valid_gstin_format(normalized["gstin"]):
            result.errors.append(RowError("gstin", "INVALID_GSTIN", f"'{normalized['gstin']}' is not a valid GSTIN"))
            return result

    result.normalized = normalized
    return result


def validate_product_row(row: dict, ctx: ImportContext) -> RowResult:
    result = RowResult()
    name = _require(row, "name")
    if not name:
        result.errors.append(RowError("name", "MISSING_REQUIRED_FIELD", "Item name is required"))
        return result

    item_type = (_require(row, "item_type") or "PRODUCT").upper()
    if item_type not in ("PRODUCT", "SERVICE"):
        result.errors.append(
            RowError("item_type", "INVALID_ITEM_TYPE", f"'{item_type}' must be PRODUCT or SERVICE")
        )
        return result

    try:
        tax_rate = normalize_optional_amount(row.get("tax_rate"))
    except NormalizationError as exc:
        result.errors.append(RowError("tax_rate", "INVALID_AMOUNT", str(exc)))
        return result

    result.normalized = {
        "name": name,
        "code": normalize_text(row.get("code")),
        "item_type": item_type,
        "hsn_sac": normalize_text(row.get("hsn_sac")),
        "unit": normalize_text(row.get("unit")),
        "tax_rate": tax_rate,
    }
    return result


def validate_ledger_row(row: dict, ctx: ImportContext) -> RowResult:
    result = RowResult()
    name = _require(row, "name")
    if not name:
        result.errors.append(RowError("name", "MISSING_REQUIRED_FIELD", "Ledger name is required"))
        return result

    ledger_type = (_require(row, "ledger_type") or "").upper()
    valid_types = {"ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE", "RECEIVABLE", "PAYABLE", "BANK", "CASH", "TAX"}
    if ledger_type not in valid_types:
        result.errors.append(
            RowError("ledger_type", "INVALID_LEDGER_TYPE", f"'{ledger_type}' is not a recognized ledger type")
        )
        return result

    try:
        opening_balance = normalize_optional_amount(row.get("opening_balance"))
    except NormalizationError as exc:
        result.errors.append(RowError("opening_balance", "INVALID_AMOUNT", str(exc)))
        return result

    balance_type = (_require(row, "opening_balance_type") or "DEBIT").upper()
    if balance_type not in ("DEBIT", "CREDIT"):
        result.errors.append(
            RowError("opening_balance_type", "INVALID_BALANCE_TYPE", f"'{balance_type}' must be DEBIT or CREDIT")
        )
        return result

    result.normalized = {
        "name": name,
        "code": normalize_text(row.get("code")),
        "ledger_type": ledger_type,
        "opening_balance": opening_balance,
        "opening_balance_type": balance_type,
    }
    return result


def validate_sales_row(row: dict, ctx: ImportContext) -> RowResult:
    result = RowResult()

    invoice_number = _require(row, "invoice_number")
    if not invoice_number:
        result.errors.append(RowError("invoice_number", "MISSING_INVOICE_NUMBER", "Invoice number is required"))

    customer_name = _require(row, "customer_name")
    if not customer_name:
        result.errors.append(RowError("customer_name", "MISSING_CUSTOMER", "Customer name is required"))
    customer_id = ctx.customers_by_name.get((customer_name or "").lower())
    if customer_name and customer_id is None:
        result.errors.append(
            RowError("customer_name", "MISSING_CUSTOMER", f"No customer named '{customer_name}' exists")
        )

    try:
        invoice_date = normalize_date(row.get("invoice_date"))
    except NormalizationError as exc:
        result.errors.append(RowError("invoice_date", "INVALID_DATE", str(exc)))
        invoice_date = None

    try:
        taxable_amount = normalize_amount(row.get("taxable_amount"))
        if taxable_amount < 0:
            raise NormalizationError("Taxable amount cannot be negative")
    except NormalizationError as exc:
        result.errors.append(RowError("taxable_amount", "INVALID_AMOUNT", str(exc)))
        taxable_amount = None

    try:
        cgst = normalize_optional_amount(row.get("cgst_amount"))
        sgst = normalize_optional_amount(row.get("sgst_amount"))
        igst = normalize_optional_amount(row.get("igst_amount"))
        cess = normalize_optional_amount(row.get("cess_amount"))
    except NormalizationError as exc:
        result.errors.append(RowError(None, "INVALID_AMOUNT", str(exc)))
        cgst = sgst = igst = cess = Decimal("0")

    if result.errors:
        return result

    result.normalized = {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "customer_id": customer_id,
        "taxable_amount": taxable_amount,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "cess_amount": cess,
        "place_of_supply": normalize_text(row.get("place_of_supply")),
        "place_of_supply_state_code": normalize_text(row.get("place_of_supply_state_code")),
    }
    return result


def validate_purchase_row(row: dict, ctx: ImportContext) -> RowResult:
    result = RowResult()

    invoice_number = _require(row, "invoice_number")
    if not invoice_number:
        result.errors.append(RowError("invoice_number", "MISSING_INVOICE_NUMBER", "Invoice number is required"))

    vendor_name = _require(row, "vendor_name")
    if not vendor_name:
        result.errors.append(RowError("vendor_name", "MISSING_VENDOR", "Vendor name is required"))
    vendor_id = ctx.vendors_by_name.get((vendor_name or "").lower())
    if vendor_name and vendor_id is None:
        result.errors.append(RowError("vendor_name", "MISSING_VENDOR", f"No vendor named '{vendor_name}' exists"))

    try:
        invoice_date = normalize_date(row.get("invoice_date"))
    except NormalizationError as exc:
        result.errors.append(RowError("invoice_date", "INVALID_DATE", str(exc)))
        invoice_date = None

    try:
        taxable_amount = normalize_amount(row.get("taxable_amount"))
        if taxable_amount < 0:
            raise NormalizationError("Taxable amount cannot be negative")
    except NormalizationError as exc:
        result.errors.append(RowError("taxable_amount", "INVALID_AMOUNT", str(exc)))
        taxable_amount = None

    try:
        cgst = normalize_optional_amount(row.get("cgst_amount"))
        sgst = normalize_optional_amount(row.get("sgst_amount"))
        igst = normalize_optional_amount(row.get("igst_amount"))
        cess = normalize_optional_amount(row.get("cess_amount"))
    except NormalizationError as exc:
        result.errors.append(RowError(None, "INVALID_AMOUNT", str(exc)))
        cgst = sgst = igst = cess = Decimal("0")

    supplier_invoice_date = None
    if row.get("supplier_invoice_date"):
        try:
            supplier_invoice_date = normalize_date(row.get("supplier_invoice_date"))
        except NormalizationError as exc:
            result.errors.append(RowError("supplier_invoice_date", "INVALID_DATE", str(exc)))

    if result.errors:
        return result

    result.normalized = {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "vendor_id": vendor_id,
        "taxable_amount": taxable_amount,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "cess_amount": cess,
        "supplier_invoice_number": normalize_text(row.get("supplier_invoice_number")),
        "supplier_invoice_date": supplier_invoice_date,
    }
    return result


def validate_payment_row(row: dict, ctx: ImportContext) -> RowResult:
    result = RowResult()
    payment_number = _require(row, "payment_number")
    if not payment_number:
        result.errors.append(RowError("payment_number", "MISSING_REQUIRED_FIELD", "Payment number is required"))

    ledger_name = _require(row, "ledger_name")
    ledger_id = ctx.ledgers_by_name.get((ledger_name or "").lower())
    if not ledger_name or ledger_id is None:
        result.errors.append(RowError("ledger_name", "INVALID_LEDGER", f"No ledger named '{ledger_name}' exists"))

    try:
        payment_date = normalize_date(row.get("payment_date"))
    except NormalizationError as exc:
        result.errors.append(RowError("payment_date", "INVALID_DATE", str(exc)))
        payment_date = None

    try:
        amount = normalize_amount(row.get("amount"))
        if amount <= 0:
            raise NormalizationError("Amount must be greater than zero")
    except NormalizationError as exc:
        result.errors.append(RowError("amount", "INVALID_AMOUNT", str(exc)))
        amount = None

    payment_mode = (_require(row, "payment_mode") or "OTHER").upper()
    if payment_mode not in ("CASH", "BANK", "UPI", "CHEQUE", "CARD", "OTHER"):
        payment_mode = "OTHER"

    if result.errors:
        return result

    result.normalized = {
        "payment_number": payment_number,
        "payment_date": payment_date,
        "ledger_id": ledger_id,
        "amount": amount,
        "payment_mode": payment_mode,
        "reference_number": normalize_text(row.get("reference_number")),
    }
    return result


def validate_receipt_row(row: dict, ctx: ImportContext) -> RowResult:
    result = RowResult()
    receipt_number = _require(row, "receipt_number")
    if not receipt_number:
        result.errors.append(RowError("receipt_number", "MISSING_REQUIRED_FIELD", "Receipt number is required"))

    customer_name = _require(row, "customer_name")
    customer_id = ctx.customers_by_name.get((customer_name or "").lower())
    if not customer_name or customer_id is None:
        result.errors.append(
            RowError("customer_name", "MISSING_CUSTOMER", f"No customer named '{customer_name}' exists")
        )

    ledger_name = _require(row, "ledger_name")
    ledger_id = ctx.ledgers_by_name.get((ledger_name or "").lower())
    if not ledger_name or ledger_id is None:
        result.errors.append(RowError("ledger_name", "INVALID_LEDGER", f"No ledger named '{ledger_name}' exists"))

    try:
        receipt_date = normalize_date(row.get("receipt_date"))
    except NormalizationError as exc:
        result.errors.append(RowError("receipt_date", "INVALID_DATE", str(exc)))
        receipt_date = None

    try:
        amount = normalize_amount(row.get("amount"))
        if amount <= 0:
            raise NormalizationError("Amount must be greater than zero")
    except NormalizationError as exc:
        result.errors.append(RowError("amount", "INVALID_AMOUNT", str(exc)))
        amount = None

    payment_mode = (_require(row, "payment_mode") or "OTHER").upper()
    if payment_mode not in ("CASH", "BANK", "UPI", "CHEQUE", "CARD", "OTHER"):
        payment_mode = "OTHER"

    if result.errors:
        return result

    result.normalized = {
        "receipt_number": receipt_number,
        "receipt_date": receipt_date,
        "customer_id": customer_id,
        "ledger_id": ledger_id,
        "amount": amount,
        "payment_mode": payment_mode,
    }
    return result


def validate_journal_row(row: dict, ctx: ImportContext) -> RowResult:
    result = RowResult()
    journal_number = _require(row, "journal_number")
    if not journal_number:
        result.errors.append(RowError("journal_number", "MISSING_REQUIRED_FIELD", "Journal number is required"))

    ledger_name = _require(row, "ledger_name")
    ledger_id = ctx.ledgers_by_name.get((ledger_name or "").lower())
    if not ledger_name or ledger_id is None:
        result.errors.append(RowError("ledger_name", "INVALID_LEDGER", f"No ledger named '{ledger_name}' exists"))

    try:
        journal_date = normalize_date(row.get("journal_date"))
    except NormalizationError as exc:
        result.errors.append(RowError("journal_date", "INVALID_DATE", str(exc)))
        journal_date = None

    try:
        debit = normalize_optional_amount(row.get("debit_amount"))
        credit = normalize_optional_amount(row.get("credit_amount"))
    except NormalizationError as exc:
        result.errors.append(RowError(None, "INVALID_AMOUNT", str(exc)))
        debit = credit = Decimal("0")

    if debit > 0 and credit > 0:
        result.errors.append(
            RowError(None, "UNBALANCED_JOURNAL", "A row cannot have both a debit and a credit amount")
        )
    if debit == 0 and credit == 0:
        result.errors.append(
            RowError(None, "UNBALANCED_JOURNAL", "A row must have either a debit or a credit amount")
        )

    if result.errors:
        return result

    result.normalized = {
        "journal_number": journal_number,
        "journal_date": journal_date,
        "ledger_id": ledger_id,
        "debit_amount": debit,
        "credit_amount": credit,
        "narration": normalize_text(row.get("narration")),
    }
    return result


def validate_gstr2b_row(row: dict, ctx: ImportContext) -> RowResult:
    from app.utils.gstin import is_valid_gstin

    result = RowResult()

    supplier_gstin = _require(row, "supplier_gstin")
    if not supplier_gstin:
        result.errors.append(
            RowError("supplier_gstin", "MISSING_GSTIN", "Supplier GSTIN is required")
        )
    elif not is_valid_gstin(supplier_gstin.upper()):
        result.errors.append(
            RowError(
                "supplier_gstin",
                "INVALID_GSTIN_FORMAT",
                f"'{supplier_gstin}' is not a structurally valid GSTIN",
            )
        )

    invoice_number = _require(row, "invoice_number")
    if not invoice_number:
        result.errors.append(
            RowError("invoice_number", "MISSING_INVOICE_NUMBER", "Invoice number is required")
        )

    try:
        invoice_date = normalize_date(row.get("invoice_date"))
    except NormalizationError as exc:
        result.errors.append(RowError("invoice_date", "INVALID_DATE", str(exc)))
        invoice_date = None

    document_type = (_require(row, "document_type") or "INVOICE").upper()
    if document_type not in ("INVOICE", "CREDIT_NOTE", "DEBIT_NOTE"):
        result.errors.append(
            RowError(
                "document_type",
                "INVALID_DOCUMENT_TYPE",
                f"'{document_type}' must be INVOICE, CREDIT_NOTE, or DEBIT_NOTE",
            )
        )

    try:
        taxable_value = normalize_amount(row.get("taxable_value"))
        if taxable_value < 0:
            raise NormalizationError("Taxable value cannot be negative")
    except NormalizationError as exc:
        result.errors.append(RowError("taxable_value", "INVALID_AMOUNT", str(exc)))
        taxable_value = None

    try:
        cgst = normalize_optional_amount(row.get("cgst_amount"))
        sgst = normalize_optional_amount(row.get("sgst_amount"))
        igst = normalize_optional_amount(row.get("igst_amount"))
        cess = normalize_optional_amount(row.get("cess_amount"))
    except NormalizationError as exc:
        result.errors.append(RowError(None, "INVALID_AMOUNT", str(exc)))
        cgst = sgst = igst = cess = Decimal("0")

    if result.errors:
        return result

    result.normalized = {
        "supplier_gstin": supplier_gstin.upper(),
        "supplier_name": normalize_text(row.get("supplier_name")),
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "document_type": document_type,
        "taxable_value": taxable_value,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "cess_amount": cess,
    }
    return result


def validate_bank_statement_row(row: dict, ctx: ImportContext) -> RowResult:
    """No ImportContext lookups needed — a bank statement row stands
    alone, unlike sales/purchase rows that resolve a party name to an id.
    Exactly one of debit/credit must be populated (PHASE6 §50); the
    normalized fields are computed here but `description` itself is
    passed through untouched (PHASE6 §11)."""
    from app.utils.bank_normalization import normalize_bank_text

    result = RowResult()

    try:
        transaction_date = normalize_date(row.get("transaction_date"))
    except NormalizationError as exc:
        result.errors.append(RowError("transaction_date", "INVALID_DATE", str(exc)))
        transaction_date = None

    value_date = None
    if row.get("value_date"):
        try:
            value_date = normalize_date(row.get("value_date"))
        except NormalizationError as exc:
            result.errors.append(RowError("value_date", "INVALID_DATE", str(exc)))

    description = normalize_text(row.get("description"))
    if not description:
        result.errors.append(
            RowError("description", "MISSING_REQUIRED_FIELD", "Description is required")
        )

    try:
        debit_amount = normalize_optional_amount(row.get("debit_amount"))
        credit_amount = normalize_optional_amount(row.get("credit_amount"))
        if debit_amount < 0 or credit_amount < 0:
            raise NormalizationError("Debit/credit amounts cannot be negative")
    except NormalizationError as exc:
        result.errors.append(RowError(None, "INVALID_AMOUNT", str(exc)))
        debit_amount = credit_amount = Decimal("0")

    if debit_amount > 0 and credit_amount > 0:
        result.errors.append(
            RowError(None, "BOTH_DEBIT_AND_CREDIT", "A row cannot have both a debit and a credit amount")
        )
    if debit_amount == 0 and credit_amount == 0:
        result.errors.append(
            RowError(None, "MISSING_AMOUNT", "A row must have either a debit or a credit amount")
        )

    balance_after = None
    if row.get("balance_after_transaction"):
        try:
            balance_after = normalize_amount(row.get("balance_after_transaction"))
        except NormalizationError as exc:
            result.errors.append(RowError("balance_after_transaction", "INVALID_AMOUNT", str(exc)))

    if result.errors:
        return result

    reference_number = normalize_text(row.get("reference_number"))
    result.normalized = {
        "transaction_date": transaction_date,
        "value_date": value_date,
        "description": description,
        "reference_number": reference_number,
        "cheque_number": normalize_text(row.get("cheque_number")),
        "debit_amount": debit_amount,
        "credit_amount": credit_amount,
        "balance_after_transaction": balance_after,
        "normalized_description": normalize_bank_text(description),
        "normalized_reference": normalize_bank_text(reference_number),
    }
    return result


def validate_tds_row(row: dict, ctx: ImportContext) -> RowResult:
    """External/actual TDS data (e.g. from last year's records or a CA's
    working file) being brought in for reconciliation — not something the
    rule engine (re)computes. `tds_amount` is required precisely because
    this is reconciliation import, not a calculation request (PHASE5
    section 29)."""
    result = RowResult()

    deductee_name = _require(row, "deductee_name")
    if not deductee_name:
        result.errors.append(RowError("deductee_name", "MISSING_DEDUCTEE", "Deductee name is required"))
    deductee_id = ctx.deductees_by_name.get((deductee_name or "").lower())
    if deductee_name and deductee_id is None:
        result.errors.append(
            RowError("deductee_name", "MISSING_DEDUCTEE", f"No deductee named '{deductee_name}' exists")
        )

    section_code = _require(row, "section_code")
    if not section_code:
        result.errors.append(RowError("section_code", "MISSING_SECTION", "TDS section is required"))
    tds_section_id = ctx.tds_sections_by_code.get((section_code or "").upper())
    if section_code and tds_section_id is None:
        result.errors.append(
            RowError("section_code", "MISSING_SECTION", f"'{section_code}' is not a known TDS section")
        )

    pan = normalize_text(row.get("pan"))
    if pan:
        from app.utils.pan import is_valid_pan

        if not is_valid_pan(pan):
            result.errors.append(RowError("pan", "INVALID_PAN", f"'{pan}' is not a structurally valid PAN"))

    try:
        transaction_date = normalize_date(row.get("transaction_date"))
    except NormalizationError as exc:
        result.errors.append(RowError("transaction_date", "INVALID_DATE", str(exc)))
        transaction_date = None

    deduction_date = None
    if row.get("deduction_date"):
        try:
            deduction_date = normalize_date(row.get("deduction_date"))
        except NormalizationError as exc:
            result.errors.append(RowError("deduction_date", "INVALID_DATE", str(exc)))

    try:
        gross_amount = normalize_amount(row.get("gross_amount"))
        if gross_amount <= 0:
            raise NormalizationError("Gross amount must be greater than zero")
    except NormalizationError as exc:
        result.errors.append(RowError("gross_amount", "INVALID_AMOUNT", str(exc)))
        gross_amount = None

    try:
        tds_amount = normalize_amount(row.get("tds_amount"))
        if tds_amount < 0:
            raise NormalizationError("TDS amount cannot be negative")
    except NormalizationError as exc:
        result.errors.append(RowError("tds_amount", "INVALID_TDS_AMOUNT", str(exc)))
        tds_amount = None

    try:
        tds_rate = normalize_optional_amount(row.get("tds_rate"))
    except NormalizationError as exc:
        result.errors.append(RowError("tds_rate", "INVALID_TDS_RATE", str(exc)))
        tds_rate = Decimal("0")

    if result.errors:
        return result

    if gross_amount is not None and tds_amount is not None and tds_amount > gross_amount:
        result.errors.append(
            RowError("tds_amount", "INVALID_TDS_AMOUNT", "TDS amount cannot exceed the gross amount")
        )
        return result

    result.normalized = {
        "deductee_id": deductee_id,
        "tds_section_id": tds_section_id,
        "pan": pan,
        "transaction_date": transaction_date,
        "deduction_date": deduction_date or transaction_date,
        "gross_amount": gross_amount,
        "tds_amount": tds_amount,
        "tds_rate": tds_rate,
    }
    return result


VALIDATORS = {
    ImportType.CUSTOMERS: validate_customer_row,
    ImportType.VENDORS: validate_vendor_row,
    ImportType.PRODUCTS: validate_product_row,
    ImportType.LEDGERS: validate_ledger_row,
    ImportType.SALES: validate_sales_row,
    ImportType.PURCHASES: validate_purchase_row,
    ImportType.PAYMENTS: validate_payment_row,
    ImportType.RECEIPTS: validate_receipt_row,
    ImportType.JOURNALS: validate_journal_row,
    ImportType.TALLY: validate_sales_row,
    ImportType.GSTR2B: validate_gstr2b_row,
    ImportType.TDS: validate_tds_row,
    ImportType.BANK_STATEMENT: validate_bank_statement_row,
}


def validate_row(import_type: ImportType, row: dict, ctx: ImportContext) -> RowResult:
    return VALIDATORS[import_type](row, ctx)
