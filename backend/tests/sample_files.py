"""Minimal, valid byte content for each supported file type, used by upload
tests. Each sample starts with the real magic-byte signature that
app.utils.file_validation checks for, so tests exercise the same signature
check production traffic goes through.
"""

MIN_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
MIN_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
MIN_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
MIN_XLSX = b"PK\x03\x04" + b"\x00" * 32
MIN_XLS = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32
MIN_CSV = b"name,amount\nInvoice 1,1000\n"

EXE_CONTENT = b"MZ\x90\x00\x03\x00\x00\x00"
