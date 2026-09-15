"""§24 — file-format adapters behind one interface.

`ImportService` only ever calls `adapter.parse(content)` — it never knows
or cares whether the bytes came from a CSV, an XLSX, or a Tally export.
Adding a new source format (or, someday, a live `TallyAPIAdapter` that
talks to Tally's ODBC/XML interface instead of a file) means adding one
class here, not touching the import pipeline.
"""

import csv
import io
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


class TallyExportAdapter(AccountingImportAdapter):
    """Tally's "Export -> CSV/Excel" produces an ordinary CSV or XLSX file
    — there is no live Tally API involved (explicitly out of scope). This
    adapter just picks the right underlying parser by extension.
    """

    def __init__(self, file_extension: str) -> None:
        self._delegate: AccountingImportAdapter = (
            ExcelImportAdapter() if file_extension in ("xlsx", "xls") else CSVImportAdapter()
        )

    def parse(self, content: bytes) -> list[dict[str, str]]:
        return self._delegate.parse(content)


def get_adapter(file_extension: str, *, is_tally: bool = False) -> AccountingImportAdapter:
    if is_tally:
        return TallyExportAdapter(file_extension)
    if file_extension in ("xlsx", "xls"):
        return ExcelImportAdapter()
    if file_extension == "csv":
        return CSVImportAdapter()
    raise ValidationAppError(
        f"Unsupported import file type: .{file_extension}", code="DOCUMENT_TYPE_NOT_SUPPORTED"
    )
