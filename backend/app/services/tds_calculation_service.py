"""Pure TDS arithmetic — the one place that turns (amount, rule, PAN
status) into a deducted amount, so no two callers (transaction creation,
return preparation, reconciliation) can compute it differently. Never
called with a missing/ambiguous rule; that determination belongs to
`TDSApplicabilityService`, which must resolve to APPLICABLE before this
runs (PHASE5 section 15-16).
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.exceptions import ValidationAppError
from app.models.tds_enums import PANStatus, TDSRateType
from app.models.tds_rule import TDSRule
from app.services.accounting_calculation_service import round_money


@dataclass
class TDSCalculationResult:
    base_amount: Decimal
    rate_type: TDSRateType
    rate_used: Decimal
    pan_status: PANStatus
    used_no_pan_rate: bool
    tds_amount: Decimal
    net_amount: Decimal
    tds_section_id: str
    tds_rule_id: str


class TDSCalculationService:
    @staticmethod
    def calculate(
        *, amount: Decimal, rule: TDSRule, pan_status: PANStatus
    ) -> TDSCalculationResult:
        if amount < 0:
            raise ValidationAppError("Amount cannot be negative", code="INVALID_AMOUNT")

        # Section 206AA: PAN unavailable/invalid means the concessional
        # rate in `rule.rate` does not apply — the higher `no_pan_rate`
        # must be used instead. A caller that reaches here with a missing
        # PAN and no `no_pan_rate` configured is a caller bug: the
        # applicability engine must have already sent this case to
        # REVIEW_REQUIRED rather than calling calculate() (PHASE5 §52).
        pan_missing = pan_status in (PANStatus.NOT_AVAILABLE, PANStatus.INVALID, PANStatus.PENDING_REVIEW)
        used_no_pan_rate = pan_missing and rule.no_pan_rate is not None
        if pan_missing and rule.no_pan_rate is None:
            raise ValidationAppError(
                "Cannot calculate TDS: PAN is unavailable and no no-PAN rate is configured "
                "for this rule",
                code="MISSING_NO_PAN_RATE",
            )

        effective_rate = rule.no_pan_rate if used_no_pan_rate else rule.rate

        if rule.rate_type == TDSRateType.PERCENTAGE:
            tds_amount = round_money(amount * effective_rate / Decimal("100"))
        else:
            tds_amount = round_money(effective_rate)
            if tds_amount > amount:
                tds_amount = round_money(amount)

        return TDSCalculationResult(
            base_amount=round_money(amount),
            rate_type=rule.rate_type,
            rate_used=effective_rate,
            pan_status=pan_status,
            used_no_pan_rate=used_no_pan_rate,
            tds_amount=tds_amount,
            net_amount=round_money(amount) - tds_amount,
            tds_section_id=str(rule.tds_section_id),
            tds_rule_id=str(rule.id),
        )
