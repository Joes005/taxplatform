"""Structural GSTIN validation.

A GSTIN is 15 characters: 2-digit state code + 10-character PAN + 1-digit
entity number + a literal 'Z' + 1 checksum character. This module only
checks that shape and recomputes the checksum — it never calls any
government service, and a structurally valid GSTIN is not proof the
registration is actually active. See PHASE4 spec section 6.
"""

import re
from dataclasses import dataclass

from app.core.gst_state_codes import GST_STATE_CODES

_GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_CHECKSUM_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def compute_gstin_check_digit(gstin_without_checksum: str) -> str:
    """Recomputes the 15th (check) character from the first 14.

    Uses the published mod-36, alternating-factor algorithm (the same
    family as a Code-39/Luhn-mod-N check digit). Verified against the
    publicly documented sample GSTINs 27AAPFU0939F1ZV and 29AABCU9603R1ZJ.
    """
    factor = 2
    total = 0
    for char in reversed(gstin_without_checksum):
        digit = _CHECKSUM_ALPHABET.index(char)
        addend = factor * digit
        factor = 1 if factor == 2 else 2
        addend = (addend // 36) + (addend % 36)
        total += addend
    remainder = total % 36
    check_digit_index = (36 - remainder) % 36
    return _CHECKSUM_ALPHABET[check_digit_index]


@dataclass
class GSTINValidationResult:
    is_valid: bool
    state_code: str | None = None
    state_name: str | None = None
    error_code: str | None = None
    error_message: str | None = None


def validate_gstin(gstin: str | None) -> GSTINValidationResult:
    """Basic structural + state-code + checksum validation only.

    Never treat `is_valid=True` as proof the GSTIN is officially
    registered/active — that requires a government API this platform does
    not call (see PHASE4 spec sections 6 and 78).
    """
    if not gstin:
        return GSTINValidationResult(
            is_valid=False, error_code="INVALID_GSTIN", error_message="GSTIN is required"
        )

    candidate = gstin.strip().upper()

    if len(candidate) != 15:
        return GSTINValidationResult(
            is_valid=False,
            error_code="INVALID_GSTIN_FORMAT",
            error_message="GSTIN must be exactly 15 characters",
        )

    if not _GSTIN_PATTERN.match(candidate):
        return GSTINValidationResult(
            is_valid=False,
            error_code="INVALID_GSTIN_FORMAT",
            error_message="GSTIN does not match the expected format",
        )

    state_code = candidate[:2]
    state_name = GST_STATE_CODES.get(state_code)
    if state_name is None:
        return GSTINValidationResult(
            is_valid=False,
            error_code="INVALID_STATE_CODE",
            error_message=f"'{state_code}' is not a recognized GST state/UT code",
        )

    expected_check_digit = compute_gstin_check_digit(candidate[:14])
    if candidate[14] != expected_check_digit:
        return GSTINValidationResult(
            is_valid=False,
            error_code="INVALID_GSTIN",
            error_message="GSTIN checksum does not match",
        )

    return GSTINValidationResult(is_valid=True, state_code=state_code, state_name=state_name)


def is_valid_gstin(gstin: str | None) -> bool:
    return validate_gstin(gstin).is_valid
