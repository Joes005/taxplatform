"""§39 — reusable column-mapping service: source column -> system field.

`suggest_mapping` gives the wizard a sensible starting point (fuzzy header
matching) that the user can always override; `apply_mapping` is the one
place a raw file row turns into a dict keyed by our field names, used by
both the parse step and the commit step so they can never drift apart.
"""

from app.core.exceptions import ValidationAppError
from app.services.imports.field_definitions import FieldDefinition, get_required_fields
from app.services.imports.normalizers import normalize_header

# Common real-world header variants, normalized, mapped to our field names.
_KNOWN_ALIASES: dict[str, str] = {
    "customername": "customer_name",
    "customer": "customer_name",
    "partyname": "customer_name",
    "party": "customer_name",
    "buyername": "customer_name",
    "vendorname": "vendor_name",
    "vendor": "vendor_name",
    "suppliername": "vendor_name",
    "supplier": "vendor_name",
    "ledgername": "ledger_name",
    "ledger": "ledger_name",
    "accountname": "ledger_name",
    "invoiceno": "invoice_number",
    "invoicenumber": "invoice_number",
    "billno": "invoice_number",
    "invoicedate": "invoice_date",
    "date": "invoice_date",
    "billdate": "invoice_date",
    "taxablevalue": "taxable_amount",
    "taxableamount": "taxable_amount",
    "amount": "amount",
    "totalamount": "taxable_amount",
    "cgst": "cgst_amount",
    "sgst": "sgst_amount",
    "igst": "igst_amount",
    "cess": "cess_amount",
    "gstin": "gstin",
    "pan": "pan",
    "email": "email",
    "emailid": "email",
    "phone": "phone",
    "mobile": "phone",
    "phonenumber": "phone",
    "state": "state",
    "statecode": "state_code",
    "pincode": "pincode",
    "pin": "pincode",
    "name": "name",
    "code": "code",
    "hsnsac": "hsn_sac",
    "hsn": "hsn_sac",
    "sac": "hsn_sac",
    "unit": "unit",
    "taxrate": "tax_rate",
    "gstrate": "tax_rate",
    "placeofsupply": "place_of_supply",
    "paymentmode": "payment_mode",
    "mode": "payment_mode",
    "referencenumber": "reference_number",
    "reference": "reference_number",
    "narration": "narration",
    "description": "narration",
    "debit": "debit_amount",
    "debitamount": "debit_amount",
    "credit": "credit_amount",
    "creditamount": "credit_amount",
}


def suggest_mapping(
    source_columns: list[str], fields: list[FieldDefinition]
) -> dict[str, str]:
    """Best-effort source_column -> field_name suggestions. Never assumes
    every file has identical headers — this is a starting point the wizard
    shows the user, not an authoritative mapping.
    """
    field_names = {f.name for f in fields}
    suggestions: dict[str, str] = {}
    for column in source_columns:
        normalized = normalize_header(column)
        target = _KNOWN_ALIASES.get(normalized)
        if target is None and normalized in field_names:
            target = normalized
        if target and target in field_names and target not in suggestions.values():
            suggestions[column] = target
    return suggestions


def validate_mapping(mapping: dict[str, str], import_type_fields: list[FieldDefinition]) -> None:
    mapped_targets = set(mapping.values())
    required = {f.name for f in import_type_fields if f.required}
    missing = required - mapped_targets
    if missing:
        raise ValidationAppError(
            f"The following required fields are not mapped to any column: {', '.join(sorted(missing))}",
            code="INCOMPLETE_COLUMN_MAPPING",
        )


def apply_mapping(raw_row: dict, mapping: dict[str, str]) -> dict:
    """`mapping` is {source_column: target_field}. Unmapped source columns
    are dropped; a target field with no source column simply isn't present
    in the result (row validators treat that as missing)."""
    mapped: dict = {}
    for source_column, target_field in mapping.items():
        if source_column in raw_row:
            mapped[target_field] = raw_row[source_column]
    return mapped
