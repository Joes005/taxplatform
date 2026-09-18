"""Bank transaction description/reference normalization (PHASE6 §11).

Deliberately light-touch: collapse whitespace, drop repeated separators,
lowercase. The original `description` on `BankTransaction` is never
touched — these functions only ever produce the separate
`normalized_description`/`normalized_reference` values the matching
engine reads, so normalization can never destroy the source-of-truth text
a human reviews.
"""

import re

_WHITESPACE_RE = re.compile(r"\s+")
_SEPARATOR_RE = re.compile(r"[/\-_.]{2,}")
_PUNCTUATION_RE = re.compile(r"[^a-z0-9\s]")


def normalize_bank_text(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = raw.strip().lower()
    if not text:
        return None
    text = _SEPARATOR_RE.sub(" ", text)
    text = _PUNCTUATION_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip() or None
