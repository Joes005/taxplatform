"""Generic, reusable GST validation findings.

Every GST module (GSTR-1, GSTR-2B import, reconciliation, GSTR-3B) reports
issues through the same `GSTValidationFinding` shape (PHASE4 section 46)
instead of inventing its own error format. This module holds the checks
shared across more than one of those callers; module-specific checks (e.g.
GSTR-1's HSN/SAC summary rules) live next to the service that owns them
and build findings with the same helper.
"""

from decimal import Decimal

from app.models.gst_enums import GSTTransactionCategory, ValidationSeverity
from app.schemas.gst_common import GSTValidationFinding
from app.utils.gstin import is_valid_gstin


def make_finding(
    *,
    code: str,
    severity: ValidationSeverity,
    entity: str,
    entity_id: str,
    message: str,
    field: str | None = None,
) -> GSTValidationFinding:
    return GSTValidationFinding(
        code=code, severity=severity, entity=entity, entity_id=entity_id, message=message, field=field
    )


class GSTValidationService:
    @staticmethod
    def validate_gstin_field(
        gstin: str | None,
        *,
        required: bool,
        entity: str,
        entity_id: str,
        field: str = "gstin",
    ) -> list[GSTValidationFinding]:
        findings: list[GSTValidationFinding] = []
        if not gstin:
            if required:
                findings.append(
                    make_finding(
                        code="MISSING_GSTIN",
                        severity=ValidationSeverity.ERROR,
                        entity=entity,
                        entity_id=entity_id,
                        message="GSTIN is required for this transaction category",
                        field=field,
                    )
                )
            return findings

        if not is_valid_gstin(gstin):
            findings.append(
                make_finding(
                    code="INVALID_GSTIN_FORMAT",
                    severity=ValidationSeverity.ERROR,
                    entity=entity,
                    entity_id=entity_id,
                    message=f"'{gstin}' is not a structurally valid GSTIN",
                    field=field,
                )
            )
        return findings

    @staticmethod
    def validate_place_of_supply(
        place_of_supply_state_code: str | None, *, entity: str, entity_id: str
    ) -> list[GSTValidationFinding]:
        if place_of_supply_state_code:
            return []
        return [
            make_finding(
                code="MISSING_PLACE_OF_SUPPLY",
                severity=ValidationSeverity.ERROR,
                entity=entity,
                entity_id=entity_id,
                message="Place of supply is required",
                field="place_of_supply_state_code",
            )
        ]

    @staticmethod
    def validate_non_negative_amounts(
        amounts: dict[str, Decimal], *, entity: str, entity_id: str
    ) -> list[GSTValidationFinding]:
        findings: list[GSTValidationFinding] = []
        for field, value in amounts.items():
            if value < 0:
                findings.append(
                    make_finding(
                        code="INVALID_AMOUNT",
                        severity=ValidationSeverity.ERROR,
                        entity=entity,
                        entity_id=entity_id,
                        message=f"{field} cannot be negative",
                        field=field,
                    )
                )
        return findings

    @staticmethod
    def validate_hsn_sac(
        hsn_sac: str | None, *, entity: str, entity_id: str
    ) -> list[GSTValidationFinding]:
        if hsn_sac:
            return []
        return [
            make_finding(
                code="MISSING_HSN_SAC",
                severity=ValidationSeverity.WARNING,
                entity=entity,
                entity_id=entity_id,
                message="HSN/SAC code is missing for this line item",
                field="hsn_sac",
            )
        ]

    @staticmethod
    def check_review_required(
        category: GSTTransactionCategory, *, entity: str, entity_id: str
    ) -> list[GSTValidationFinding]:
        if category != GSTTransactionCategory.REVIEW_REQUIRED:
            return []
        return [
            make_finding(
                code="REVIEW_REQUIRED",
                severity=ValidationSeverity.WARNING,
                entity=entity,
                entity_id=entity_id,
                message="Insufficient data to classify this transaction with confidence",
            )
        ]
