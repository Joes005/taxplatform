"""Structural TAN validation.

A TAN is 10 characters: 4 letters (the first 3 identify the jurisdiction,
the 4th the deductor's initial), 5 digits, 1 letter. Unlike GSTIN, TAN has
no publicly documented checksum algorithm, so this module checks format
only and never claims a TAN is officially allotted/active. See PHASE5
spec section 6.
"""

import re
from dataclasses import dataclass

_TAN_PATTERN = re.compile(r"^[A-Z]{4}[0-9]{5}[A-Z]$")


@dataclass
class TANValidationResult:
    is_valid: bool
    error_code: str | None = None
    error_message: str | None = None


def validate_tan(tan: str | None) -> TANValidationResult:
    if not tan:
        return TANValidationResult(
            is_valid=False, error_code="INVALID_TAN", error_message="TAN is required"
        )

    candidate = tan.strip().upper()

    if len(candidate) != 10:
        return TANValidationResult(
            is_valid=False,
            error_code="INVALID_TAN_FORMAT",
            error_message="TAN must be exactly 10 characters",
        )

    if not _TAN_PATTERN.match(candidate):
        return TANValidationResult(
            is_valid=False,
            error_code="INVALID_TAN_FORMAT",
            error_message="TAN does not match the expected format (AAAA99999A)",
        )

    return TANValidationResult(is_valid=True)


def is_valid_tan(tan: str | None) -> bool:
    return validate_tan(tan).is_valid
