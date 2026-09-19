"""The central Income Tax computation orchestrator (PHASE8 §31, §42,
§96). `calculate()` always re-reads every underlying `(company_id,
financial_year_id)`-scoped row live — nothing here is incrementally
patched — and every successful calculation is snapshotted, so a later
rule-set or data change never silently rewrites history (PHASE8 §71).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.income_tax_enums import TaxComputationStatus
from app.models.tax_computation import TaxComputation, TaxComputationSnapshot
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.income_tax_capital_gain_repository import IncomeTaxCapitalGainRepository
from app.repositories.income_tax_deduction_repository import IncomeTaxDeductionRepository
from app.repositories.income_tax_income_repository import (
    IncomeTaxHousePropertyIncomeRepository,
    IncomeTaxOtherIncomeRepository,
    IncomeTaxSalaryIncomeRepository,
)
from app.repositories.tax_computation_repository import TaxComputationRepository, TaxComputationSnapshotRepository
from app.schemas.tax_computation import TaxComputationCreate
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.business_income_service import BusinessIncomeCalculationService
from app.services.deduction_service import eligible_amount_for
from app.services.income_tax_calculator import compute_gross_tax_liability
from app.services.income_tax_loss_service import IncomeTaxLossService
from app.services.income_tax_profile_service import IncomeTaxProfileService
from app.services.income_tax_rule_service import IncomeTaxRuleService
from app.services.income_tax_year_service import assessment_year_for
from app.services.tax_credit_service import (
    IncomeTaxAdvanceTaxPaymentService,
    IncomeTaxSelfAssessmentTaxPaymentService,
    TaxCreditService,
)

ZERO = Decimal("0")

_ALLOWED_CALCULATE_STATUSES = {
    TaxComputationStatus.DRAFT,
    TaxComputationStatus.CALCULATED,
    TaxComputationStatus.REVIEW_REQUIRED,
}

_TRANSITIONS: dict[tuple[TaxComputationStatus, str], TaxComputationStatus] = {
    (TaxComputationStatus.CALCULATED, "submit_review"): TaxComputationStatus.READY_FOR_REVIEW,
    (TaxComputationStatus.REVIEW_REQUIRED, "submit_review"): TaxComputationStatus.READY_FOR_REVIEW,
    (TaxComputationStatus.READY_FOR_REVIEW, "approve"): TaxComputationStatus.APPROVED,
    (TaxComputationStatus.APPROVED, "lock"): TaxComputationStatus.LOCKED,
    (TaxComputationStatus.DRAFT, "cancel"): TaxComputationStatus.CANCELLED,
    (TaxComputationStatus.CALCULATED, "cancel"): TaxComputationStatus.CANCELLED,
    (TaxComputationStatus.REVIEW_REQUIRED, "cancel"): TaxComputationStatus.CANCELLED,
    (TaxComputationStatus.READY_FOR_REVIEW, "cancel"): TaxComputationStatus.CANCELLED,
}

_AUDIT_ACTION_BY_ACTION = {
    "submit_review": AuditAction.TAX_COMPUTATION_SUBMITTED,
    "approve": AuditAction.TAX_COMPUTATION_APPROVED,
    "lock": AuditAction.TAX_COMPUTATION_LOCKED,
    "cancel": AuditAction.TAX_COMPUTATION_CANCELLED,
}


class IncomeTaxComputationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TaxComputationRepository(db)
        self.snapshot_repo = TaxComputationSnapshotRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.profiles = IncomeTaxProfileService(db)
        self.rules = IncomeTaxRuleService(db)
        self.salary = IncomeTaxSalaryIncomeRepository(db)
        self.house_property = IncomeTaxHousePropertyIncomeRepository(db)
        self.other_income = IncomeTaxOtherIncomeRepository(db)
        self.capital_gains = IncomeTaxCapitalGainRepository(db)
        self.deductions = IncomeTaxDeductionRepository(db)
        self.business_income = BusinessIncomeCalculationService(db)
        self.losses = IncomeTaxLossService(db)
        self.credits = TaxCreditService(db)
        self.advance_tax = IncomeTaxAdvanceTaxPaymentService(db)
        self.self_assessment_tax = IncomeTaxSelfAssessmentTaxPaymentService(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: TaxComputationCreate, current_user: User, meta: RequestMeta
    ) -> TaxComputation:
        fy = await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id)
        if fy is None:
            raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")
        if await self.repo.get_active_for_fy(company_id, fy.id) is not None:
            raise ConflictError(
                "An active tax computation already exists for this financial year",
                code="TAX_COMPUTATION_ALREADY_EXISTS",
            )

        computation = TaxComputation(
            company_id=company_id,
            financial_year_id=fy.id,
            assessment_year=assessment_year_for(fy),
            tax_regime=payload.tax_regime,
            status=TaxComputationStatus.DRAFT,
            created_by=current_user.id,
        )
        await self.repo.create(computation)

        await self.audit.log(
            action=AuditAction.TAX_COMPUTATION_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tax_computation",
            resource_id=str(computation.id),
            description=f"Tax computation created for AY {computation.assessment_year} ({computation.tax_regime.value})",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return computation

    async def get(self, company_id: uuid.UUID, computation_id: uuid.UUID) -> TaxComputation:
        computation = await self.repo.get_by_id_for_company(computation_id, company_id)
        if computation is None:
            raise NotFoundError("Tax computation not found", code="TAX_COMPUTATION_NOT_FOUND")
        return computation

    async def list_for_company(self, company_id: uuid.UUID, *, page: int, page_size: int):
        return await self.repo.list_for_company(company_id, offset=(page - 1) * page_size, limit=page_size)

    async def calculate(
        self, company_id: uuid.UUID, computation_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> TaxComputation:
        computation = await self.get(company_id, computation_id)
        if computation.status not in _ALLOWED_CALCULATE_STATUSES:
            raise ConflictError(
                f"Cannot recalculate a computation in status {computation.status.value}",
                code="INVALID_TAX_COMPUTATION_TRANSITION",
            )

        profile = await self.profiles.get_optional(company_id)
        if profile is None:
            raise ValidationAppError(
                "An Income Tax profile is required before running a computation",
                code="INCOME_TAX_PROFILE_REQUIRED",
            )

        rule_set = await self.rules.get_active_rule_set(
            assessment_year=computation.assessment_year,
            taxpayer_type=profile.taxpayer_type,
            tax_regime=computation.tax_regime,
        )
        computation.rule_set_id = rule_set.id

        salary_rows = await self.salary.list_for_fy(company_id, computation.financial_year_id)
        salary_income = sum((r.taxable_amount for r in salary_rows), ZERO)

        hp_rows = await self.house_property.list_for_fy(company_id, computation.financial_year_id)
        house_property_income = sum((r.income_or_loss for r in hp_rows), ZERO)

        business_breakdown = await self.business_income.calculate(company_id, computation.financial_year_id)
        business_income = business_breakdown.taxable_business_income

        cg_rows = await self.capital_gains.list_for_fy(company_id, computation.financial_year_id)
        capital_gains_income = sum((r.gain_amount for r in cg_rows), ZERO)

        other_rows = await self.other_income.list_for_fy(company_id, computation.financial_year_id)
        other_income = sum((r.net_amount for r in other_rows), ZERO)

        loss_setoff = await self.losses.total_setoff_for_fy(company_id, computation.financial_year_id)

        gross_total_income = max(
            salary_income + house_property_income + business_income + capital_gains_income + other_income - loss_setoff,
            ZERO,
        )

        deduction_rows = await self.deductions.list_for_fy(company_id, computation.financial_year_id)
        total_deductions = sum((eligible_amount_for(d, rule_set) for d in deduction_rows), ZERO)
        total_deductions = min(total_deductions, gross_total_income)

        taxable_income = round_money(gross_total_income - total_deductions)

        (
            tax_before_rebate,
            rebate,
            surcharge,
            cess,
            gross_tax_liability,
            surcharge_applied,
        ) = compute_gross_tax_liability(taxable_income, rule_set)

        tds_credit_total = await self.credits.total_tds_credit_for_fy(company_id, computation.financial_year_id)
        advance_tax_total = await self.advance_tax.total_for_fy(company_id, computation.financial_year_id)
        self_assessment_tax_total = await self.self_assessment_tax.total_for_fy(
            company_id, computation.financial_year_id
        )

        balance = round_money(
            gross_tax_liability - tds_credit_total - advance_tax_total - self_assessment_tax_total
        )

        computation.salary_income = round_money(salary_income)
        computation.house_property_income = round_money(house_property_income)
        computation.business_income = round_money(business_income)
        computation.capital_gains_income = round_money(capital_gains_income)
        computation.other_income = round_money(other_income)
        computation.gross_total_income = round_money(gross_total_income)
        computation.total_deductions = round_money(total_deductions)
        computation.taxable_income = taxable_income
        computation.tax_before_rebate = tax_before_rebate
        computation.rebate = rebate
        computation.tax_after_rebate = round_money(tax_before_rebate - rebate)
        computation.surcharge = surcharge
        computation.cess = cess
        computation.gross_tax_liability = gross_tax_liability
        computation.tds_credit_total = round_money(tds_credit_total)
        computation.advance_tax_total = round_money(advance_tax_total)
        computation.self_assessment_tax_total = round_money(self_assessment_tax_total)
        computation.balance_payable_or_refund = balance
        computation.calculated_at = datetime.now(timezone.utc)

        needs_review = surcharge_applied or bool(business_breakdown.review_required_ledger_ids)
        computation.status = (
            TaxComputationStatus.REVIEW_REQUIRED if needs_review else TaxComputationStatus.CALCULATED
        )

        await self.db.flush()
        await self.db.refresh(computation)

        version = await self.snapshot_repo.next_version(computation.id)
        snapshot = TaxComputationSnapshot(
            company_id=company_id,
            tax_computation_id=computation.id,
            rule_set_id=rule_set.id,
            version=version,
            generated_at=datetime.now(timezone.utc),
            generated_by=current_user.id,
            summary_data={
                "assessment_year": computation.assessment_year,
                "tax_regime": computation.tax_regime.value,
                "rule_set_version": rule_set.version,
                "salary_income": str(computation.salary_income),
                "house_property_income": str(computation.house_property_income),
                "business_income": str(computation.business_income),
                "capital_gains_income": str(computation.capital_gains_income),
                "other_income": str(computation.other_income),
                "gross_total_income": str(computation.gross_total_income),
                "total_deductions": str(computation.total_deductions),
                "taxable_income": str(computation.taxable_income),
                "tax_before_rebate": str(computation.tax_before_rebate),
                "rebate": str(computation.rebate),
                "surcharge": str(computation.surcharge),
                "cess": str(computation.cess),
                "gross_tax_liability": str(computation.gross_tax_liability),
                "tds_credit_total": str(computation.tds_credit_total),
                "advance_tax_total": str(computation.advance_tax_total),
                "self_assessment_tax_total": str(computation.self_assessment_tax_total),
                "balance_payable_or_refund": str(computation.balance_payable_or_refund),
                "business_income_breakdown": {
                    "revenue": str(business_breakdown.revenue),
                    "purchases": str(business_breakdown.purchases),
                    "eligible_expenses": str(business_breakdown.eligible_expenses),
                    "disallowances": str(business_breakdown.disallowances),
                    "other_adjustments": str(business_breakdown.other_adjustments),
                    "depreciation_adjustments": str(business_breakdown.depreciation_adjustments),
                },
            },
        )
        await self.snapshot_repo.create(snapshot)

        await self.audit.log(
            action=AuditAction.TAX_COMPUTATION_CALCULATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tax_computation",
            resource_id=str(computation.id),
            description=f"Tax computation calculated: {computation.status.value}, "
            f"balance {computation.balance_payable_or_refund}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return computation

    async def _transition(
        self, company_id: uuid.UUID, computation_id: uuid.UUID, action: str, current_user: User, meta: RequestMeta
    ) -> TaxComputation:
        computation = await self.get(company_id, computation_id)
        key = (computation.status, action)
        if key not in _TRANSITIONS:
            raise ConflictError(
                f"Cannot {action.replace('_', ' ')} a computation in status {computation.status.value}",
                code="INVALID_TAX_COMPUTATION_TRANSITION",
            )
        computation.status = _TRANSITIONS[key]
        if action == "approve":
            computation.approved_by = current_user.id
            computation.approved_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(computation)

        await self.audit.log(
            action=_AUDIT_ACTION_BY_ACTION[action],
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tax_computation",
            resource_id=str(computation.id),
            description=f"Tax computation moved to {computation.status.value}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return computation

    async def submit_for_review(self, company_id, computation_id, current_user, meta) -> TaxComputation:
        return await self._transition(company_id, computation_id, "submit_review", current_user, meta)

    async def approve(self, company_id, computation_id, current_user, meta) -> TaxComputation:
        return await self._transition(company_id, computation_id, "approve", current_user, meta)

    async def lock(self, company_id, computation_id, current_user, meta) -> TaxComputation:
        return await self._transition(company_id, computation_id, "lock", current_user, meta)

    async def cancel(self, company_id, computation_id, current_user, meta) -> TaxComputation:
        return await self._transition(company_id, computation_id, "cancel", current_user, meta)

    async def list_snapshots(self, computation_id: uuid.UUID):
        return await self.snapshot_repo.list_for_computation(computation_id)
