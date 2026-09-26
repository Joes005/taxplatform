"""§24 — file-format adapters behind one interface.

`ImportService` only ever calls `adapter.parse(content)` — it never knows
or cares whether the bytes came from a CSV, an XLSX, or a Tally export.
Adding a new source format (or, someday, a live `TallyAPIAdapter` that
talks to Tally's ODBC/XML interface instead of a file) means adding one
class here, not touching the import pipeline.
"""

import csv
import io
import json
from abc import ABC, abstractmethod

from openpyxl import load_workbook

from app.core.exceptions import ValidationAppError


class AccountingImportAdapter(ABC):
    @abstractmethod
    def parse(self, content: bytes) -> list[dict[str, str]]:
        """Returns one dict per data row, keyed by the file's own header
        row — column mapping to system fields happens later, in
        column_mapping.py, not here."""


class CSVImportAdapter(AccountingImportAdapter):
    def parse(self, content: bytes) -> list[dict[str, str]]:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise ValidationAppError("CSV file has no header row", code="INVALID_FILE")
        return [dict(row) for row in reader]


class ExcelImportAdapter(AccountingImportAdapter):
    def parse(self, content: bytes) -> list[dict[str, str]]:
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as exc:  # noqa: BLE001 - openpyxl raises various formats for bad files
            raise ValidationAppError("Could not read this Excel file", code="INVALID_FILE") from exc

        sheet = workbook.active
        rows_iter = sheet.iter_rows(values_only=True)
        try:
            header = [str(h).strip() if h is not None else "" for h in next(rows_iter)]
        except StopIteration:
            raise ValidationAppError("Excel file has no header row", code="INVALID_FILE") from None

        rows = []
        for raw_row in rows_iter:
            if all(cell is None for cell in raw_row):
                continue
            rows.append({header[i]: raw_row[i] for i in range(len(header)) if i < len(raw_row)})
        return rows


class JSONImportAdapter(AccountingImportAdapter):
    """Parses a flat JSON array of objects — e.g. `[{"supplier_gstin": ...,
    "invoice_number": ...}, ...]`. This is deliberately not the GST
    portal's deeply-nested GSTR-2B download schema (grouped by supplier,
    by document type, ...): without a real reference file to test against,
    claiming to parse that nested format would be exactly the kind of
    unverified support PHASE4 section 26 says to avoid. A GSTR-2B export
    already flattened to one row per document (as this platform's own
    sample files are) parses correctly; a raw portal JSON download does
    not yet.
    """

    def parse(self, content: bytes) -> list[dict[str, str]]:
        try:
            data = json.loads(content.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationAppError("Could not parse this JSON file", code="INVALID_FILE") from exc

        if isinstance(data, dict):
            data = data.get("records") or data.get("data") or data.get("rows")

        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise ValidationAppError(
                "JSON import expects a flat array of row objects (or {\"records\": [...]})",
                code="INVALID_FILE",
            )
        return data


class TallyXMLImportAdapter(AccountingImportAdapter):
    """Parses Tally XML exports and flattens vouchers into row dictionaries
    for the generic column-mapping import pipeline."""

    def parse(self, content: bytes) -> list[dict[str, str]]:
        from app.services.tally.tally_xml_parser import TallyXMLParser

        parser = TallyXMLParser()
        batch = parser.parse(content)
        rows: list[dict[str, str]] = []
        for v in batch.vouchers:
            tb = v.tax_breakdown
            rows.append({
                "invoice_number": v.voucher_number,
                "invoice_date": v.voucher_date.isoformat(),
                "customer_name": v.party_name or "",
                "party_name": v.party_name or "",
                "taxable_amount": str(tb.taxable_amount),
                "cgst_amount": str(tb.cgst_amount),
                "sgst_amount": str(tb.sgst_amount),
                "igst_amount": str(tb.igst_amount),
                "cess_amount": str(tb.cess_amount),
                "total_amount": str(v.total_amount),
                "narration": v.narration or "",
                "voucher_type": v.voucher_type,
            })
        return rows


class TallyExportAdapter(AccountingImportAdapter):
    """Tally's "Export -> XML/CSV/Excel" produces XML, CSV, or XLSX files.
    This adapter picks the right underlying parser by extension.
    """

    def __init__(self, file_extension: str) -> None:
        if file_extension == "xml":
            self._delegate: AccountingImportAdapter = TallyXMLImportAdapter()
        elif file_extension in ("xlsx", "xls"):
            self._delegate = ExcelImportAdapter()
        else:
            self._delegate = CSVImportAdapter()

    def parse(self, content: bytes) -> list[dict[str, str]]:
        return self._delegate.parse(content)


def get_adapter(file_extension: str, *, is_tally: bool = False) -> AccountingImportAdapter:
    if is_tally:
        return TallyExportAdapter(file_extension)
    if file_extension in ("xlsx", "xls"):
        return ExcelImportAdapter()
    if file_extension == "csv":
        return CSVImportAdapter()
    if file_extension == "xml":
        return TallyXMLImportAdapter()
    if file_extension == "json":
        return JSONImportAdapter()
    raise ValidationAppError(
        f"Unsupported import file type: .{file_extension}", code="DOCUMENT_TYPE_NOT_SUPPORTED"
    )
