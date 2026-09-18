"""Generic, reusable TDS validation findings — every TDS module (imports,
transactions, return preparation) reports issues through the same
`TDSValidationFinding` shape (PHASE5 section 40) instead of inventing its
own error format, mirroring `GSTValidationService`.
"""

from decimal import Decimal

from app.models.tds_enums import PANStatus, TDSApplicabilityStatus, TDSValidationSeverity
from app.schemas.tds_common import TDSValidationFinding
from app.utils.pan import is_valid_pan


def make_finding(
    *,
    code: str,
    severity: TDSValidationSeverity,
    entity: str,
    entity_id: str,
    message: str,
    field: str | None = None,
) -> TDSValidationFinding:
    return TDSValidationFinding(
        code=code, severity=severity, entity=entity, entity_id=entity_id, message=message, field=field
    )


class TDSValidationService:
    @staticmethod
    def validate_pan_field(
        pan: str | None, pan_status: PANStatus, *, entity: str, entity_id: str
    ) -> list[TDSValidationFinding]:
        findings: list[TDSValidationFinding] = []
        if pan_status == PANStatus.NOT_AVAILABLE:
            findings.append(
                make_finding(
                    code="MISSING_PAN",
                    severity=TDSValidationSeverity.WARNING,
                    entity=entity,
                    entity_id=entity_id,
                    message="Deductee PAN is not on file — the higher no-PAN rate applies",
                    field="pan",
                )
            )
            return findings

        if pan_status == PANStatus.INVALID or (pan and not is_valid_pan(pan)):
            findings.append(
                make_finding(
                    code="INVALID_PAN",
                    severity=TDSValidationSeverity.ERROR,
                    entity=entity,
                    entity_id=entity_id,
                    message=f"'{pan}' is not a structurally valid PAN",
                    field="pan",
                )
            )
        return findings

    @staticmethod
    def validate_non_negative_amounts(
        amounts: dict[str, Decimal], *, entity: str, entity_id: str
    ) -> list[TDSValidationFinding]:
        findings: list[TDSValidationFinding] = []
        for field, value in amounts.items():
            if value < 0:
                findings.append(
                    make_finding(
                        code="INVALID_AMOUNT",
                        severity=TDSValidationSeverity.ERROR,
                        entity=entity,
                        entity_id=entity_id,
                        message=f"{field} cannot be negative",
                        field=field,
                    )
                )
        return findings

    @staticmethod
    def check_review_required(
        status: TDSApplicabilityStatus, reason: str, *, entity: str, entity_id: str
    ) -> list[TDSValidationFinding]:
        if status not in (TDSApplicabilityStatus.REVIEW_REQUIRED, TDSApplicabilityStatus.MISSING_DATA):
            return []
        return [
            make_finding(
                code="REVIEW_REQUIRED" if status == TDSApplicabilityStatus.REVIEW_REQUIRED else "MISSING_DATA",
                severity=TDSValidationSeverity.WARNING,
                entity=entity,
                entity_id=entity_id,
                message=reason,
            )
        ]

    @staticmethod
    def validate_missing_challan(
        has_challan: bool, *, entity: str, entity_id: str
    ) -> list[TDSValidationFinding]:
        if has_challan:
            return []
        return [
            make_finding(
                code="MISSING_CHALLAN",
                severity=TDSValidationSeverity.WARNING,
                entity=entity,
                entity_id=entity_id,
                message="TDS was deducted but no challan has been allocated to it yet",
            )
        ]
