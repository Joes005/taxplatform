import io
import re
from typing import BinaryIO

from app.core.exceptions import ValidationAppError
from app.services.tally.tally_models import TallyFormat

MAX_IMPORT_FILE_SIZE_MB = 50
MAX_IMPORT_FILE_SIZE_BYTES = MAX_IMPORT_FILE_SIZE_MB * 1024 * 1024
MAX_IMPORT_RECORDS = 50000
MAX_PREVIEW_RECORDS = 100


class FileInspectionResult:
    def __init__(
        self,
        format: TallyFormat,
        detected_encoding: str = "utf-8",
        is_valid: bool = True,
        error_message: str | None = None,
        file_size: int = 0,
        has_tally_markers: bool = False,
    ) -> None:
        self.format = format
        self.detected_encoding = detected_encoding
        self.is_valid = is_valid
        self.error_message = error_message
        self.file_size = file_size
        self.has_tally_markers = has_tally_markers


def detect_tally_format(
    content: bytes,
    filename: str = "",
    mime_type: str | None = None,
) -> FileInspectionResult:
    """Reliable format detection using magic bytes, content structure,
    and fallback filename extension. Never trusts extension alone."""

    file_size = len(content)
    if file_size > MAX_IMPORT_FILE_SIZE_BYTES:
        return FileInspectionResult(
            format=TallyFormat.INVALID,
            is_valid=False,
            error_message=f"File exceeds maximum allowed size of {MAX_IMPORT_FILE_SIZE_MB}MB",
            file_size=file_size,
        )

    if file_size == 0:
        return FileInspectionResult(
            format=TallyFormat.INVALID,
            is_valid=False,
            error_message="Uploaded file is empty",
            file_size=0,
        )

    # 1. Check for Zip / Excel Magic Bytes: PK\x03\x04
    if content.startswith(b"PK\x03\x04"):
        # Excel .xlsx or zip container
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext in ("xlsx", "xlsm", "xlsb") or mime_type in (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ):
            return FileInspectionResult(
                format=TallyFormat.XLSX,
                file_size=file_size,
            )
        # Could still be an XLSX without extension
        try:
            from openpyxl import load_workbook
            load_workbook(io.BytesIO(content), read_only=True)
            return FileInspectionResult(
                format=TallyFormat.XLSX,
                file_size=file_size,
            )
        except Exception:
            return FileInspectionResult(
                format=TallyFormat.UNSUPPORTED,
                is_valid=False,
                error_message="Zip file is not a valid Excel workbook",
                file_size=file_size,
            )

    # 2. Inspect text content (first 16KB sample)
    sample_bytes = content[:16384]
    encoding = "utf-8"
    sample_text = ""
    for enc in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            sample_text = sample_bytes.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue

    if not sample_text:
        return FileInspectionResult(
            format=TallyFormat.INVALID,
            is_valid=False,
            error_message="Could not decode file content with supported encodings",
            file_size=file_size,
        )

    sample_upper = sample_text.upper().strip()

    # 3. Check for XML
    if sample_upper.startswith("<?XML") or "<ENVELOPE" in sample_upper or "<TALLYMESSAGE" in sample_upper or "<VOUCHER" in sample_upper:
        # Check Tally-specific markers
        has_tally_markers = any(marker in sample_upper for marker in (
            "<ENVELOPE",
            "<TALLYMESSAGE",
            "<HEADER>",
            "<BODY><DATA>",
            "<VOUCHERTYPENAME>",
            "<ALLLEDGERENTRIES.LIST>",
            "<LEDGERENTRIES.LIST>",
            "<STATICVARIABLES>",
        ))
        if has_tally_markers:
            return FileInspectionResult(
                format=TallyFormat.TALLY_XML,
                detected_encoding=encoding,
                file_size=file_size,
                has_tally_markers=True,
            )
        # Generic XML
        return FileInspectionResult(
            format=TallyFormat.XML,
            detected_encoding=encoding,
            file_size=file_size,
            has_tally_markers=False,
        )

    # 4. Check for CSV / TSV
    # If the text has rows with comma/tab delimiters
    lines = [ln.strip() for ln in sample_text.splitlines() if ln.strip()]
    if lines:
        first_line = lines[0]
        # Check commas or tabs
        comma_count = first_line.count(",")
        tab_count = first_line.count("\t")
        if comma_count >= 1 or tab_count >= 1:
            ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
            if ext in ("csv", "txt", "tsv") or comma_count >= 2:
                return FileInspectionResult(
                    format=TallyFormat.CSV,
                    detected_encoding=encoding,
                    file_size=file_size,
                )

    # 5. Fallback based on extension if content looks like text
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "xml":
        return FileInspectionResult(
            format=TallyFormat.XML,
            detected_encoding=encoding,
            file_size=file_size,
        )
    if ext == "csv":
        return FileInspectionResult(
            format=TallyFormat.CSV,
            detected_encoding=encoding,
            file_size=file_size,
        )

    return FileInspectionResult(
        format=TallyFormat.UNSUPPORTED,
        is_valid=False,
        error_message=f"Unsupported format or unrecognized file structure: {filename}",
        file_size=file_size,
    )
