"""Structural PAN validation.

A PAN is 10 characters: 5 letters, 4 digits, 1 letter. This module only
checks that shape — it never calls the Income Tax e-filing portal, and a
structurally valid PAN is not proof the PAN is actually allotted or active.
See PHASE5 spec section 8.
"""

import re
from dataclasses import dataclass

_PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


@dataclass
class PANValidationResult:
    is_valid: bool
    error_code: str | None = None
    error_message: str | None = None


def validate_pan(pan: str | None) -> PANValidationResult:
    if not pan:
        return PANValidationResult(
            is_valid=False, error_code="INVALID_PAN", error_message="PAN is required"
        )

    candidate = pan.strip().upper()

    if len(candidate) != 10:
        return PANValidationResult(
            is_valid=False,
            error_code="INVALID_PAN_FORMAT",
            error_message="PAN must be exactly 10 characters",
        )

    if not _PAN_PATTERN.match(candidate):
        return PANValidationResult(
            is_valid=False,
            error_code="INVALID_PAN_FORMAT",
            error_message="PAN does not match the expected format (AAAAA9999A)",
        )

    return PANValidationResult(is_valid=True)


def is_valid_pan(pan: str | None) -> bool:
    return validate_pan(pan).is_valid
