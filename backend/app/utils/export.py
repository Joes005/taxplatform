"""Shared CSV and XLSX export utilities for Tally Tax.

Provides centralized helpers for rendering tabular data into CSV (UTF-8-sig)
and Excel (XLSX) format, supporting both simple flat tables and multi-section
reports.
"""

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import io
from typing import Any, Literal

from openpyxl import Workbook

ExportFormat = Literal["csv", "xlsx"]

CSV_MEDIA_TYPE = "text/csv; charset=utf-8"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass
class ExportSection:
    title: str
    headers: list[str]
    rows: list[list[Any]]


@dataclass
class ExportFile:
    content: bytes
    filename: str
    media_type: str


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def write_csv(
    headers: list[str] | None = None,
    rows: list[list[Any]] | None = None,
    title: str | None = None,
    *,
    report_type: str | None = None,
    gstin: str | None = None,
    period_label: str | None = None,
    sections: list[ExportSection] | None = None,
) -> bytes:
    """Generate CSV bytes with UTF-8-sig encoding for universal Excel compatibility.

    Supports either a simple flat table (headers, rows, optional title) or
    a structured multi-section report (report_type, gstin, period_label, sections).
    """
    buf = io.StringIO()
    writer = csv.writer(buf)

    if sections is not None:
        if report_type:
            writer.writerow([report_type])
        if gstin is not None:
            writer.writerow(["Company GSTIN", gstin])
        if period_label is not None:
            writer.writerow(["Return Period", period_label])
        writer.writerow(["Generated At", datetime.now(timezone.utc).isoformat()])
        writer.writerow([])
        for section in sections:
            if section.title:
                writer.writerow([section.title])
            writer.writerow(section.headers)
            for row in section.rows:
                writer.writerow([_stringify(v) for v in row])
            writer.writerow([])
    else:
        if title:
            writer.writerow([title])
            writer.writerow(["Generated At", datetime.now(timezone.utc).isoformat()])
            writer.writerow([])
        if headers is not None:
            writer.writerow(headers)
        if rows:
            for row in rows:
                writer.writerow([_stringify(v) for v in row])

    return buf.getvalue().encode("utf-8-sig")


def write_xlsx(
    headers: list[str] | None = None,
    rows: list[list[Any]] | None = None,
    sheet_name: str = "Sheet1",
    title: str | None = None,
    *,
    report_type: str | None = None,
    gstin: str | None = None,
    period_label: str | None = None,
    sections: list[ExportSection] | None = None,
) -> bytes:
    """Generate Excel XLSX bytes.

    Supports either a single-sheet table (headers, rows, sheet_name, optional title)
    or a multi-sheet report with a Cover sheet (report_type, gstin, period_label, sections).
    """
    workbook = Workbook()

    if sections is not None:
        cover = workbook.active
        cover.title = "Cover"
        if report_type:
            cover.append([report_type])
        if gstin is not None:
            cover.append(["Company GSTIN", gstin])
        if period_label is not None:
            cover.append(["Return Period", period_label])
        cover.append(["Generated At", datetime.now(timezone.utc).isoformat()])

        used_titles: set[str] = set()
        for section in sections:
            t = section.title[:31] or "Sheet"
            suffix = 1
            base_t = t
            while t in used_titles:
                suffix += 1
                t = f"{base_t[:28]}-{suffix}"
            used_titles.add(t)

            sheet = workbook.create_sheet(title=t)
            sheet.append(section.headers)
            for row in section.rows:
                sheet.append([_stringify(v) for v in row])
    else:
        sheet = workbook.active
        sheet.title = (sheet_name or "Sheet1")[:31]
        if title:
            sheet.append([title])
            sheet.append(["Generated At", datetime.now(timezone.utc).isoformat()])
            sheet.append([])
        if headers is not None:
            sheet.append(headers)
        if rows:
            for row in rows:
                sheet.append([_stringify(v) for v in row])

    buf = io.BytesIO()
    workbook.save(buf)
    return buf.getvalue()


def render_export(
    *,
    headers: list[str],
    rows: list[list[Any]],
    title: str,
    fmt: ExportFormat,
    filename_stub: str,
    sheet_name: str = "Sheet1",
) -> ExportFile:
    """Helper to render either CSV or XLSX ExportFile from flat tabular data."""
    if fmt == "xlsx":
        content = write_xlsx(headers=headers, rows=rows, sheet_name=sheet_name, title=title)
        return ExportFile(
            content=content,
            filename=f"{filename_stub}.xlsx",
            media_type=XLSX_MEDIA_TYPE,
        )
    content = write_csv(headers=headers, rows=rows, title=title)
    return ExportFile(
        content=content,
        filename=f"{filename_stub}.csv",
        media_type=CSV_MEDIA_TYPE,
    )
