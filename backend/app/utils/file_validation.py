"""Upload validation: extension, declared MIME type, and file signature
("magic bytes"). None of these are trusted alone — a client can lie about
all three — so a file is accepted only when extension, MIME type, and (where
the format has a reliable signature) the actual leading bytes all agree.
"""

from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class FileTypeSpec:
    extension: str
    allowed_mime_types: frozenset[str]
    # None means "no reliable fixed signature" (e.g. CSV) — content is
    # instead checked for being plausible text rather than binary junk.
    magic_bytes: tuple[bytes, ...] | None


FILE_TYPE_REGISTRY: dict[str, FileTypeSpec] = {
    "pdf": FileTypeSpec(
        extension="pdf",
        allowed_mime_types=frozenset({"application/pdf"}),
        magic_bytes=(b"%PDF-",),
    ),
    "jpg": FileTypeSpec(
        extension="jpg",
        allowed_mime_types=frozenset({"image/jpeg"}),
        magic_bytes=(b"\xff\xd8\xff",),
    ),
    "jpeg": FileTypeSpec(
        extension="jpeg",
        allowed_mime_types=frozenset({"image/jpeg"}),
        magic_bytes=(b"\xff\xd8\xff",),
    ),
    "png": FileTypeSpec(
        extension="png",
        allowed_mime_types=frozenset({"image/png"}),
        magic_bytes=(b"\x89PNG\r\n\x1a\n",),
    ),
    "xlsx": FileTypeSpec(
        extension="xlsx",
        allowed_mime_types=frozenset(
            {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/zip",
                "application/octet-stream",
            }
        ),
        # XLSX is a ZIP container; the PK signature is the strongest check
        # available without fully parsing the archive.
        magic_bytes=(b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ),
    "xls": FileTypeSpec(
        extension="xls",
        allowed_mime_types=frozenset({"application/vnd.ms-excel", "application/octet-stream"}),
        # Legacy XLS is an OLE2 compound file.
        magic_bytes=(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ),
    "csv": FileTypeSpec(
        extension="csv",
        allowed_mime_types=frozenset(
            {"text/csv", "application/vnd.ms-excel", "text/plain", "application/csv", ""}
        ),
        magic_bytes=None,
    ),
    "json": FileTypeSpec(
        extension="json",
        allowed_mime_types=frozenset({"application/json", "text/json", "text/plain", ""}),
        magic_bytes=None,
    ),
    "xml": FileTypeSpec(
        extension="xml",
        allowed_mime_types=frozenset({"application/xml", "text/xml", "text/plain", ""}),
        magic_bytes=None,
    ),
}


class FileValidationError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        self.code = code
        super().__init__(message)


def _looks_like_text(content: bytes, *, sample_size: int = 8192) -> bool:
    sample = content[:sample_size]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            sample.decode("latin-1")
            return True
        except UnicodeDecodeError:
            return False


def validate_file(
    *,
    filename: str,
    declared_mime_type: str | None,
    content: bytes,
    allowed_extensions: set[str],
) -> FileTypeSpec:
    """Validate a file's extension, declared MIME type, and content signature.

    Returns the matched FileTypeSpec on success, or raises
    FileValidationError with a specific error code on the first check that
    fails.
    """
    if "." not in filename or filename.startswith("."):
        raise FileValidationError("File has no recognizable extension", code="INVALID_FILE")

    extension = filename.rsplit(".", 1)[-1].lower()

    if extension not in allowed_extensions:
        raise FileValidationError(
            f"File type .{extension} is not supported", code="DOCUMENT_TYPE_NOT_SUPPORTED"
        )

    spec = FILE_TYPE_REGISTRY.get(extension)
    if spec is None:
        # Defensive: ALLOWED_DOCUMENT_EXTENSIONS can only ever narrow this
        # registry (see Settings.allowed_document_extensions), so this
        # should be unreachable — but never accept a type we cannot verify.
        raise FileValidationError(
            f"File type .{extension} is not supported", code="DOCUMENT_TYPE_NOT_SUPPORTED"
        )

    mime = (declared_mime_type or "").lower().split(";")[0].strip()
    if mime not in spec.allowed_mime_types:
        raise FileValidationError(
            f"Declared content type '{declared_mime_type}' does not match a .{extension} file",
            code="INVALID_FILE",
        )

    if not content:
        raise FileValidationError("File is empty", code="INVALID_FILE")

    if spec.magic_bytes is not None:
        if not any(content.startswith(sig) for sig in spec.magic_bytes):
            raise FileValidationError(
                "File content does not match its extension (failed signature check)",
                code="INVALID_FILE",
            )
    else:
        if not _looks_like_text(content):
            raise FileValidationError(
                "File content does not look like a valid text/CSV file", code="INVALID_FILE"
            )

    return spec


def safe_content_disposition(filename: str, *, disposition_type: str = "attachment") -> str:
    """Builds a Content-Disposition value that can't be used to inject or
    corrupt headers via a crafted filename (quotes, control characters, an
    embedded CRLF, ...). `filename` is user-supplied (the original upload
    name) and must never be interpolated into a header raw — this mirrors
    the safe encoding Starlette's FileResponse already applies internally,
    for the one code path (a non-local StorageProvider) that builds the
    header manually instead of going through FileResponse.
    """
    encoded = quote(filename)
    if encoded != filename:
        return f"{disposition_type}; filename*=utf-8''{encoded}"
    return f'{disposition_type}; filename="{filename}"'
