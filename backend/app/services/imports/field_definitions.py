"""§39 — the target fields each import type maps source columns onto.
Drives both the frontend mapping-wizard step and server-side "did the user
map every required field" validation before parsing proceeds.
"""

from dataclasses import dataclass

from app.models.accounting_enums import ImportType


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    label: str
    required: bool = False


CUSTOMER_FIELDS = [
    FieldDefinition("name", "Customer Name", required=True),
    FieldDefinition("code", "Customer Code"),
    FieldDefinition("gstin", "GSTIN"),
    FieldDefinition("pan", "PAN"),
    FieldDefinition("email", "Email"),
    FieldDefinition("phone", "Phone"),
    FieldDefinition("billing_address", "Billing Address"),
    FieldDefinition("state", "State"),
    FieldDefinition("state_code", "State Code"),
    FieldDefinition("pincode", "Pincode"),
]

VENDOR_FIELDS = [
    FieldDefinition("name", "Vendor Name", required=True),
    FieldDefinition("code", "Vendor Code"),
    FieldDefinition("gstin", "GSTIN"),
    FieldDefinition("pan", "PAN"),
    FieldDefinition("email", "Email"),
    FieldDefinition("phone", "Phone"),
    FieldDefinition("address", "Address"),
    FieldDefinition("state", "State"),
    FieldDefinition("state_code", "State Code"),
    FieldDefinition("pincode", "Pincode"),
]

PRODUCT_FIELDS = [
    FieldDefinition("name", "Item Name", required=True),
    FieldDefinition("code", "Item Code"),
    FieldDefinition("item_type", "Item Type (PRODUCT/SERVICE)", required=True),
    FieldDefinition("hsn_sac", "HSN/SAC"),
    FieldDefinition("unit", "Unit"),
    FieldDefinition("tax_rate", "Tax Rate %"),
]

LEDGER_FIELDS = [
    FieldDefinition("name", "Ledger Name", required=True),
    FieldDefinition("code", "Ledger Code"),
    FieldDefinition("ledger_type", "Ledger Type", required=True),
    FieldDefinition("opening_balance", "Opening Balance"),
    FieldDefinition("opening_balance_type", "Opening Balance Type (DEBIT/CREDIT)"),
]

SALES_FIELDS = [
    FieldDefinition("invoice_number", "Invoice Number", required=True),
    FieldDefinition("invoice_date", "Invoice Date", required=True),
    FieldDefinition("customer_name", "Customer Name", required=True),
    FieldDefinition("taxable_amount", "Taxable Amount", required=True),
    FieldDefinition("cgst_amount", "CGST Amount"),
    FieldDefinition("sgst_amount", "SGST Amount"),
    FieldDefinition("igst_amount", "IGST Amount"),
    FieldDefinition("cess_amount", "Cess Amount"),
    FieldDefinition("place_of_supply", "Place of Supply"),
]

PURCHASE_FIELDS = [
    FieldDefinition("invoice_number", "Invoice Number", required=True),
    FieldDefinition("invoice_date", "Invoice Date", required=True),
    FieldDefinition("vendor_name", "Vendor Name", required=True),
    FieldDefinition("taxable_amount", "Taxable Amount", required=True),
    FieldDefinition("cgst_amount", "CGST Amount"),
    FieldDefinition("sgst_amount", "SGST Amount"),
    FieldDefinition("igst_amount", "IGST Amount"),
    FieldDefinition("cess_amount", "Cess Amount"),
]

PAYMENT_FIELDS = [
    FieldDefinition("payment_number", "Payment Number", required=True),
    FieldDefinition("payment_date", "Payment Date", required=True),
    FieldDefinition("ledger_name", "Ledger Name", required=True),
    FieldDefinition("amount", "Amount", required=True),
    FieldDefinition("payment_mode", "Payment Mode", required=True),
    FieldDefinition("reference_number", "Reference Number"),
]

RECEIPT_FIELDS = [
    FieldDefinition("receipt_number", "Receipt Number", required=True),
    FieldDefinition("receipt_date", "Receipt Date", required=True),
    FieldDefinition("customer_name", "Customer Name", required=True),
    FieldDefinition("ledger_name", "Ledger Name", required=True),
    FieldDefinition("amount", "Amount", required=True),
    FieldDefinition("payment_mode", "Payment Mode", required=True),
]

JOURNAL_FIELDS = [
    FieldDefinition("journal_number", "Journal Number", required=True),
    FieldDefinition("journal_date", "Journal Date", required=True),
    FieldDefinition("ledger_name", "Ledger Name", required=True),
    FieldDefinition("debit_amount", "Debit Amount"),
    FieldDefinition("credit_amount", "Credit Amount"),
    FieldDefinition("narration", "Narration"),
]

FIELD_DEFINITIONS_BY_TYPE: dict[ImportType, list[FieldDefinition]] = {
    ImportType.CUSTOMERS: CUSTOMER_FIELDS,
    ImportType.VENDORS: VENDOR_FIELDS,
    ImportType.PRODUCTS: PRODUCT_FIELDS,
    ImportType.LEDGERS: LEDGER_FIELDS,
    ImportType.SALES: SALES_FIELDS,
    ImportType.PURCHASES: PURCHASE_FIELDS,
    ImportType.PAYMENTS: PAYMENT_FIELDS,
    ImportType.RECEIPTS: RECEIPT_FIELDS,
    ImportType.JOURNALS: JOURNAL_FIELDS,
    # A Tally CSV/XLSX export is structurally a sales-register-style
    # export in practice; reuse the SALES mapping rather than inventing a
    # separate schema for it.
    ImportType.TALLY: SALES_FIELDS,
}


def get_field_definitions(import_type: ImportType) -> list[FieldDefinition]:
    return FIELD_DEFINITIONS_BY_TYPE[import_type]


def get_required_fields(import_type: ImportType) -> list[str]:
    return [f.name for f in get_field_definitions(import_type) if f.required]
