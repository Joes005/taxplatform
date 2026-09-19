"""Chapter VI-A-style deduction CRUD (PHASE8 §18-19). `eligible_amount`
on the stored row is a display default (`= claimed_amount` until a
computation actually runs) — the regime-specific eligibility check
(section allowed under this regime? capped at `max_amount`?) can only be
answered once a specific `IncomeTaxRuleSet` is known, which only exists
in the context of one `TaxComputation`. `IncomeTaxComputationService`
recomputes the true eligible amount for each deduction against the
computation's own rule set every time it calculates — it never trusts
this row's stored value as authoritative for tax purposes.
"""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.income_tax_deduction import IncomeTaxDeduction
from app.models.income_tax_rule_set import IncomeTaxDeductionRule, IncomeTaxRuleSet
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.income_tax_deduction_repository import IncomeTaxDeductionRepository
from app.schemas.income_tax_deduction import IncomeTaxDeductionCreate, IncomeTaxDeductionUpdate
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

ZERO = Decimal("0")


def eligible_amount_for(deduction: IncomeTaxDeduction, rule_set: IncomeTaxRuleSet | None) -> Decimal:
    """Pure eligibility check used by both the deduction CRUD (as a
    display default) and `IncomeTaxComputationService` (as the
    authoritative figure fed into the computation)."""
    if rule_set is None:
        return round_money(deduction.claimed_amount)

    rule: IncomeTaxDeductionRule | None = next(
        (r for r in rule_set.deduction_rules if r.section_code == deduction.section_code), None
    )
    if rule is None:
        return ZERO
    allowed = rule.allowed_in_new_regime if rule_set.tax_regime.value == "NEW_REGIME" else rule.allowed_in_old_regime
    if not allowed:
        return ZERO
    if rule.max_amount is not None:
        return round_money(min(deduction.claimed_amount, rule.max_amount))
    return round_money(deduction.claimed_amount)


class DeductionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxDeductionRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxDeductionCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxDeduction:
        if await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id) is None:
            raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")

        entity = IncomeTaxDeduction(company_id=company_id, **payload.model_dump())
        entity.eligible_amount = eligible_amount_for(entity, None)
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_DEDUCTION_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_deduction",
            resource_id=str(entity.id),
            description=f"Deduction claimed: {entity.section_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxDeduction]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def get(self, company_id: uuid.UUID, entity_id: uuid.UUID) -> IncomeTaxDeduction:
        entity = await self.repo.get_by_id_for_company(entity_id, company_id)
        if entity is None:
            raise NotFoundError("Deduction not found", code="TAX_DEDUCTION_NOT_FOUND")
        return entity

    async def update(
        self,
        company_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: IncomeTaxDeductionUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> IncomeTaxDeduction:
        entity = await self.get(company_id, entity_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        entity.eligible_amount = eligible_amount_for(entity, None)
        await self.db.flush()
        await self.db.refresh(entity)

        await self.audit.log(
            action=AuditAction.TAX_DEDUCTION_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_deduction",
            resource_id=str(entity.id),
            description="Deduction updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def delete(self, company_id: uuid.UUID, entity_id: uuid.UUID, current_user: User, meta: RequestMeta) -> None:
        entity = await self.get(company_id, entity_id)
        await self.repo.delete(entity)
        await self.audit.log(
            action=AuditAction.TAX_DEDUCTION_DELETED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_deduction",
            resource_id=str(entity_id),
            description="Deduction deleted",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
