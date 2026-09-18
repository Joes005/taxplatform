"""Decides whether TDS applies to one payment — the only place that
question is answered. Every branch that cannot be confidently resolved
from the data on hand returns REVIEW_REQUIRED or MISSING_DATA rather than
guessing (PHASE5 sections 3, 14, 52) — the caller is expected to route
those to a human before any deduction is recorded.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deductee import Deductee
from app.models.tds_enums import PANStatus, TDSApplicabilityStatus
from app.models.tds_rule import TDSRule
from app.repositories.tds_rule_repository import TDSRuleRepository


@dataclass
class TDSApplicabilityResult:
    status: TDSApplicabilityStatus
    reason: str
    rule: TDSRule | None = None


class TDSApplicabilityService:
    def __init__(self, db: AsyncSession) -> None:
        self.rules = TDSRuleRepository(db)

    async def evaluate(
        self,
        company_id: uuid.UUID,
        *,
        tds_section_id: uuid.UUID,
        deductee: Deductee | None,
        transaction_date: date | None,
        amount: Decimal | None,
        aggregate_paid_this_year: Decimal | None = None,
    ) -> TDSApplicabilityResult:
        if deductee is None or transaction_date is None or amount is None:
            return TDSApplicabilityResult(
                status=TDSApplicabilityStatus.MISSING_DATA,
                reason="Deductee, transaction date, and amount are all required to evaluate TDS",
            )

        rule = await self.rules.find_effective_rule(
            company_id,
            tds_section_id=tds_section_id,
            deductee_type=deductee.deductee_type,
            as_of=transaction_date,
        )
        if rule is None:
            return TDSApplicabilityResult(
                status=TDSApplicabilityStatus.REVIEW_REQUIRED,
                reason="No effective TDS rule is configured for this section on the transaction date",
            )

        if deductee.pan_status == PANStatus.INVALID:
            return TDSApplicabilityResult(
                status=TDSApplicabilityStatus.REVIEW_REQUIRED,
                reason="Deductee PAN is marked invalid — resolve the PAN before deducting TDS",
                rule=rule,
            )

        pan_missing = deductee.pan_status in (PANStatus.NOT_AVAILABLE, PANStatus.PENDING_REVIEW)
        if pan_missing and rule.no_pan_rate is None:
            return TDSApplicabilityResult(
                status=TDSApplicabilityStatus.REVIEW_REQUIRED,
                reason="Deductee PAN is unavailable and this rule has no configured no-PAN rate",
                rule=rule,
            )

        applicable_by_single = amount > rule.threshold_amount

        applicable_by_aggregate = False
        if rule.aggregate_threshold_amount is not None:
            if aggregate_paid_this_year is None:
                return TDSApplicabilityResult(
                    status=TDSApplicabilityStatus.REVIEW_REQUIRED,
                    reason=(
                        "This section has an aggregate annual threshold but the deductee's "
                        "year-to-date payments were not provided"
                    ),
                    rule=rule,
                )
            applicable_by_aggregate = (aggregate_paid_this_year + amount) > rule.aggregate_threshold_amount

        if not applicable_by_single and not applicable_by_aggregate:
            return TDSApplicabilityResult(
                status=TDSApplicabilityStatus.NOT_APPLICABLE,
                reason=f"Amount is at or below the section's threshold of {rule.threshold_amount}",
                rule=rule,
            )

        return TDSApplicabilityResult(
            status=TDSApplicabilityStatus.APPLICABLE,
            reason="Amount exceeds the applicable threshold for this section",
            rule=rule,
        )
