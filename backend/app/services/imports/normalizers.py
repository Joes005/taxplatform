"""§25 — Normalization Layer.

Real-world exports are messy: dates in three different formats, amounts
with currency symbols and thousands separators, column headers that vary
file to file. These functions turn that mess into the clean Python types
(date, Decimal) the rest of the system trusts — every amount that reaches
an accounting table has been through `normalize_amount`, never a raw
string.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

_DATE_FORMATS = [
    "%Y-%m-%d",  # 2026-04-01 (ISO)
    "%d/%m/%Y",  # 01/04/2026
    "%d-%m-%Y",  # 01-04-2026
    "%d-%b-%Y",  # 01-Apr-2026
    "%d %b %Y",  # 01 Apr 2026
    "%m/%d/%Y",  # 04/01/2026 (US-style, tried last — ambiguous with d/m/Y)
]

_AMOUNT_STRIP_PATTERN = re.compile(r"[₹$,\s]")


class NormalizationError(ValueError):
    pass


def normalize_date(raw: str | date | datetime | None) -> date:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise NormalizationError("Date is required")
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw

    text = str(raw).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise NormalizationError(f"'{raw}' is not a recognizable date")


def normalize_amount(raw: str | int | float | Decimal | None) -> Decimal:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise NormalizationError("Amount is required")
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))

    text = _AMOUNT_STRIP_PATTERN.sub("", str(raw))
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    if not text:
        raise NormalizationError(f"'{raw}' is not a recognizable amount")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise NormalizationError(f"'{raw}' is not a recognizable amount") from exc
    return -value if negative else value


def normalize_optional_amount(raw: str | int | float | Decimal | None) -> Decimal:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return Decimal("0")
    return normalize_amount(raw)


def normalize_text(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def normalize_header(header: str) -> str:
    """Loosely normalizes a source column header for fuzzy matching during
    auto-mapping suggestions — "Party Name", "party_name", "PartyName" all
    collapse to "partyname".
    """
    return re.sub(r"[^a-z0-9]", "", header.strip().lower())
