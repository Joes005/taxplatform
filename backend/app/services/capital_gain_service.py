import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.income_tax_capital_gain import IncomeTaxCapitalGain
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.income_tax_capital_gain_repository import IncomeTaxCapitalGainRepository
from app.schemas.income_tax_capital_gain import IncomeTaxCapitalGainCreate, IncomeTaxCapitalGainUpdate
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class CapitalGainService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxCapitalGainRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    @staticmethod
    def _compute_gain(entity: IncomeTaxCapitalGain) -> None:
        cost = entity.indexed_cost if entity.indexed_cost is not None else (entity.purchase_cost + entity.improvement_cost)
        entity.gain_amount = round_money(entity.sale_consideration - entity.transfer_expenses - cost)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxCapitalGainCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxCapitalGain:
        if await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id) is None:
            raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")
        if payload.sale_date < payload.purchase_date:
            raise ValidationAppError("Sale date cannot be before purchase date", code="INVALID_CAPITAL_GAIN_DATES")

        entity = IncomeTaxCapitalGain(company_id=company_id, **payload.model_dump())
        self._compute_gain(entity)
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.CAPITAL_GAIN_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_capital_gain",
            resource_id=str(entity.id),
            description=f"Capital gain recorded: {entity.asset_description}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxCapitalGain]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def get(self, company_id: uuid.UUID, entity_id: uuid.UUID) -> IncomeTaxCapitalGain:
        entity = await self.repo.get_by_id_for_company(entity_id, company_id)
        if entity is None:
            raise NotFoundError("Capital gain not found", code="CAPITAL_GAIN_NOT_FOUND")
        return entity

    async def update(
        self,
        company_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: IncomeTaxCapitalGainUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> IncomeTaxCapitalGain:
        entity = await self.get(company_id, entity_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        self._compute_gain(entity)
        await self.db.flush()
        await self.db.refresh(entity)

        await self.audit.log(
            action=AuditAction.CAPITAL_GAIN_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_capital_gain",
            resource_id=str(entity.id),
            description="Capital gain updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def delete(self, company_id: uuid.UUID, entity_id: uuid.UUID, current_user: User, meta: RequestMeta) -> None:
        entity = await self.get(company_id, entity_id)
        await self.repo.delete(entity)
        await self.audit.log(
            action=AuditAction.CAPITAL_GAIN_DELETED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_capital_gain",
            resource_id=str(entity_id),
            description="Capital gain deleted",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

    @staticmethod
    def totals_by_type(gains: list[IncomeTaxCapitalGain]) -> tuple[Decimal, Decimal]:
        short_term = sum((g.gain_amount for g in gains if g.gain_type.value == "SHORT_TERM"), Decimal("0"))
        long_term = sum((g.gain_amount for g in gains if g.gain_type.value == "LONG_TERM"), Decimal("0"))
        return short_term, long_term
