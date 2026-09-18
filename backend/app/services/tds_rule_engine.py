"""The single entry point `TDSTransactionService` calls to go from a
payment to a deduction decision (PHASE5 section 49):

    Transaction -> Deductee -> Section -> Effective Rule -> Applicability
        -> Calculation -> explanation

Composes `TDSApplicabilityService` and `TDSCalculationService` rather than
re-implementing either — this module's only job is the orchestration and
the human-readable trace an auditor reads to answer "why did the system
deduct this amount?" (PHASE5 section 51).
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deductee import Deductee
from app.models.tds_enums import TDSApplicabilityStatus
from app.services.tds_applicability_service import TDSApplicabilityService
from app.services.tds_calculation_service import TDSCalculationResult, TDSCalculationService


@dataclass
class TDSRuleEngineResult:
    status: TDSApplicabilityStatus
    reason: str
    tds_section_id: uuid.UUID | None = None
    tds_rule_id: uuid.UUID | None = None
    calculation: TDSCalculationResult | None = None


class TDSRuleEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.applicability = TDSApplicabilityService(db)

    async def evaluate(
        self,
        company_id: uuid.UUID,
        *,
        tds_section_id: uuid.UUID,
        deductee: Deductee | None,
        transaction_date: date | None,
        amount: Decimal | None,
        aggregate_paid_this_year: Decimal | None = None,
    ) -> TDSRuleEngineResult:
        applicability = await self.applicability.evaluate(
            company_id,
            tds_section_id=tds_section_id,
            deductee=deductee,
            transaction_date=transaction_date,
            amount=amount,
            aggregate_paid_this_year=aggregate_paid_this_year,
        )

        if applicability.status != TDSApplicabilityStatus.APPLICABLE:
            return TDSRuleEngineResult(
                status=applicability.status,
                reason=applicability.reason,
                tds_rule_id=applicability.rule.id if applicability.rule else None,
                tds_section_id=applicability.rule.tds_section_id if applicability.rule else None,
            )

        assert applicability.rule is not None and deductee is not None and amount is not None
        calculation = TDSCalculationService.calculate(
            amount=amount, rule=applicability.rule, pan_status=deductee.pan_status
        )
        return TDSRuleEngineResult(
            status=TDSApplicabilityStatus.APPLICABLE,
            reason=applicability.reason,
            tds_section_id=applicability.rule.tds_section_id,
            tds_rule_id=applicability.rule.id,
            calculation=calculation,
        )
