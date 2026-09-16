import re

_NON_ALNUM = re.compile(r"[^A-Z0-9]")


def normalize_invoice_number(value: str | None) -> str:
    """Collapses common formatting differences so "INV-001", "INV001" and
    "inv 001" compare equal — used only as a fallback match key (PHASE4
    section 31, Level 2); the original value is always preserved alongside
    it, never overwritten."""
    if not value:
        return ""
    return _NON_ALNUM.sub("", value.upper())
