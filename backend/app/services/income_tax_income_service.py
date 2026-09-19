"""Salary/house-property/other-sources/exempt income CRUD (PHASE8 §21-22,
§28-29). Each service computes its entity's one derived total on
write — never left for the frontend to compute, per PHASE8 §99 ("no
hard-coded tax law in frontend").
"""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.income_tax_enums import HousePropertyType
from app.models.income_tax_income import (
    IncomeTaxExemptIncome,
    IncomeTaxHousePropertyIncome,
    IncomeTaxOtherIncome,
    IncomeTaxSalaryIncome,
)
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.income_tax_income_repository import (
    IncomeTaxExemptIncomeRepository,
    IncomeTaxHousePropertyIncomeRepository,
    IncomeTaxOtherIncomeRepository,
    IncomeTaxSalaryIncomeRepository,
)
from app.schemas.income_tax_income import (
    IncomeTaxExemptIncomeCreate,
    IncomeTaxHousePropertyIncomeCreate,
    IncomeTaxHousePropertyIncomeUpdate,
    IncomeTaxOtherIncomeCreate,
    IncomeTaxOtherIncomeUpdate,
    IncomeTaxSalaryIncomeCreate,
    IncomeTaxSalaryIncomeUpdate,
)
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

ZERO = Decimal("0")

_HOUSE_PROPERTY_STANDARD_DEDUCTION_RATE = Decimal("0.30")


async def _require_financial_year(fy_repo: FinancialYearRepository, company_id: uuid.UUID, financial_year_id):
    fy = await fy_repo.get_by_id_for_company(financial_year_id, company_id)
    if fy is None:
        raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")
    return fy


class IncomeTaxSalaryIncomeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxSalaryIncomeRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    @staticmethod
    def _compute_taxable(entity: IncomeTaxSalaryIncome) -> None:
        total = (
            entity.gross_salary
            + entity.allowances
            + entity.perquisites
            + entity.profit_in_lieu
            - entity.standard_deduction
            - entity.professional_tax
        )
        entity.taxable_amount = round_money(max(total, ZERO))

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxSalaryIncomeCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxSalaryIncome:
        await _require_financial_year(self.fy_repo, company_id, payload.financial_year_id)
        entity = IncomeTaxSalaryIncome(company_id=company_id, **payload.model_dump())
        self._compute_taxable(entity)
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_INCOME_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_salary_income",
            resource_id=str(entity.id),
            description=f"Salary income recorded for {entity.employer_name}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxSalaryIncome]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def get(self, company_id: uuid.UUID, entity_id: uuid.UUID) -> IncomeTaxSalaryIncome:
        entity = await self.repo.get_by_id_for_company(entity_id, company_id)
        if entity is None:
            raise NotFoundError("Salary income not found", code="TAX_INCOME_NOT_FOUND")
        return entity

    async def update(
        self,
        company_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: IncomeTaxSalaryIncomeUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> IncomeTaxSalaryIncome:
        entity = await self.get(company_id, entity_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        self._compute_taxable(entity)
        await self.db.flush()
        await self.db.refresh(entity)

        await self.audit.log(
            action=AuditAction.TAX_INCOME_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_salary_income",
            resource_id=str(entity.id),
            description="Salary income updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def delete(self, company_id: uuid.UUID, entity_id: uuid.UUID, current_user: User, meta: RequestMeta) -> None:
        entity = await self.get(company_id, entity_id)
        await self.repo.delete(entity)
        await self.audit.log(
            action=AuditAction.TAX_INCOME_DELETED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_salary_income",
            resource_id=str(entity_id),
            description="Salary income deleted",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )


class IncomeTaxHousePropertyIncomeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxHousePropertyIncomeRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    @staticmethod
    def _compute(entity: IncomeTaxHousePropertyIncome) -> None:
        """PHASE8 §22 — the ₹2,00,000 self-occupied home-loan-interest cap
        is deliberately NOT enforced here (a real, current tax-law figure
        this platform does not assert); `interest_on_home_loan` is used
        as entered, and a CA should verify it against the applicable cap
        before approval."""
        entity.net_annual_value = round_money(max(entity.gross_rent - entity.municipal_tax, ZERO))
        if entity.property_type == HousePropertyType.LET_OUT:
            entity.standard_deduction = round_money(
                entity.net_annual_value * _HOUSE_PROPERTY_STANDARD_DEDUCTION_RATE
            )
        else:
            entity.standard_deduction = ZERO
        entity.income_or_loss = round_money(
            entity.net_annual_value - entity.standard_deduction - entity.interest_on_home_loan
        )

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxHousePropertyIncomeCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxHousePropertyIncome:
        await _require_financial_year(self.fy_repo, company_id, payload.financial_year_id)
        entity = IncomeTaxHousePropertyIncome(company_id=company_id, **payload.model_dump())
        self._compute(entity)
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_INCOME_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_house_property_income",
            resource_id=str(entity.id),
            description="House property income recorded",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> list[IncomeTaxHousePropertyIncome]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def get(self, company_id: uuid.UUID, entity_id: uuid.UUID) -> IncomeTaxHousePropertyIncome:
        entity = await self.repo.get_by_id_for_company(entity_id, company_id)
        if entity is None:
            raise NotFoundError("House property income not found", code="TAX_INCOME_NOT_FOUND")
        return entity

    async def update(
        self,
        company_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: IncomeTaxHousePropertyIncomeUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> IncomeTaxHousePropertyIncome:
        entity = await self.get(company_id, entity_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        self._compute(entity)
        await self.db.flush()
        await self.db.refresh(entity)

        await self.audit.log(
            action=AuditAction.TAX_INCOME_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_house_property_income",
            resource_id=str(entity.id),
            description="House property income updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def delete(self, company_id: uuid.UUID, entity_id: uuid.UUID, current_user: User, meta: RequestMeta) -> None:
        entity = await self.get(company_id, entity_id)
        await self.repo.delete(entity)
        await self.audit.log(
            action=AuditAction.TAX_INCOME_DELETED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_house_property_income",
            resource_id=str(entity_id),
            description="House property income deleted",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )


class IncomeTaxOtherIncomeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxOtherIncomeRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    @staticmethod
    def _compute(entity: IncomeTaxOtherIncome) -> None:
        entity.net_amount = round_money(entity.gross_amount - entity.tds)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxOtherIncomeCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxOtherIncome:
        await _require_financial_year(self.fy_repo, company_id, payload.financial_year_id)
        entity = IncomeTaxOtherIncome(company_id=company_id, **payload.model_dump())
        self._compute(entity)
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_INCOME_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_other_income",
            resource_id=str(entity.id),
            description=f"Other income recorded: {entity.income_type}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxOtherIncome]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def get(self, company_id: uuid.UUID, entity_id: uuid.UUID) -> IncomeTaxOtherIncome:
        entity = await self.repo.get_by_id_for_company(entity_id, company_id)
        if entity is None:
            raise NotFoundError("Other income not found", code="TAX_INCOME_NOT_FOUND")
        return entity

    async def update(
        self,
        company_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: IncomeTaxOtherIncomeUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> IncomeTaxOtherIncome:
        entity = await self.get(company_id, entity_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        self._compute(entity)
        await self.db.flush()
        await self.db.refresh(entity)

        await self.audit.log(
            action=AuditAction.TAX_INCOME_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_other_income",
            resource_id=str(entity.id),
            description="Other income updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def delete(self, company_id: uuid.UUID, entity_id: uuid.UUID, current_user: User, meta: RequestMeta) -> None:
        entity = await self.get(company_id, entity_id)
        await self.repo.delete(entity)
        await self.audit.log(
            action=AuditAction.TAX_INCOME_DELETED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_other_income",
            resource_id=str(entity_id),
            description="Other income deleted",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )


class IncomeTaxExemptIncomeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxExemptIncomeRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxExemptIncomeCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxExemptIncome:
        await _require_financial_year(self.fy_repo, company_id, payload.financial_year_id)
        entity = IncomeTaxExemptIncome(company_id=company_id, **payload.model_dump())
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_INCOME_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_exempt_income",
            resource_id=str(entity.id),
            description=f"Exempt income recorded: {entity.section_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxExemptIncome]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def delete(self, company_id: uuid.UUID, entity_id: uuid.UUID, current_user: User, meta: RequestMeta) -> None:
        entity = await self.repo.get_by_id_for_company(entity_id, company_id)
        if entity is None:
            raise NotFoundError("Exempt income not found", code="TAX_INCOME_NOT_FOUND")
        await self.repo.delete(entity)
        await self.audit.log(
            action=AuditAction.TAX_INCOME_DELETED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_exempt_income",
            resource_id=str(entity_id),
            description="Exempt income deleted",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
