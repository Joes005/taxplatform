import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_enums import ComplianceCategory, ComplianceModule
from app.models.compliance_obligation import ComplianceObligation


class ComplianceObligationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, obligation: ComplianceObligation) -> ComplianceObligation:
        self.db.add(obligation)
        await self.db.flush()
        return obligation

    async def get_by_id_for_company(
        self, obligation_id: uuid.UUID, company_id: uuid.UUID
    ) -> ComplianceObligation | None:
        result = await self.db.execute(
            select(ComplianceObligation).where(
                ComplianceObligation.id == obligation_id, ComplianceObligation.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_natural_key(
        self, company_id: uuid.UUID, code: str, financial_year_id: uuid.UUID | None, tax_period: str | None
    ) -> ComplianceObligation | None:
        result = await self.db.execute(
            select(ComplianceObligation).where(
                ComplianceObligation.company_id == company_id,
                ComplianceObligation.code == code,
                ComplianceObligation.financial_year_id == financial_year_id,
                ComplianceObligation.tax_period == tax_period,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        category: ComplianceCategory | None = None,
        module: ComplianceModule | None = None,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ComplianceObligation], int]:
        query = select(ComplianceObligation).where(ComplianceObligation.company_id == company_id)
        if category is not None:
            query = query.where(ComplianceObligation.category == category)
        if module is not None:
            query = query.where(ComplianceObligation.module == module)
        if active_only:
            query = query.where(ComplianceObligation.active.is_(True))

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(ComplianceObligation.due_date.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_due_in_range(
        self, company_id: uuid.UUID, *, start: date, end: date
    ) -> list[ComplianceObligation]:
        result = await self.db.execute(
            select(ComplianceObligation).where(
                ComplianceObligation.company_id == company_id,
                ComplianceObligation.active.is_(True),
                ComplianceObligation.due_date >= start,
                ComplianceObligation.due_date <= end,
            )
        )
        return list(result.scalars().all())
