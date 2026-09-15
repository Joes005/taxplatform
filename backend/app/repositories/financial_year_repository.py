import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_year import FinancialYear


class FinancialYearRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, fy: FinancialYear) -> FinancialYear:
        self.db.add(fy)
        await self.db.flush()
        return fy

    async def get_by_id_for_company(
        self, fy_id: uuid.UUID, company_id: uuid.UUID
    ) -> FinancialYear | None:
        result = await self.db.execute(
            select(FinancialYear).where(
                FinancialYear.id == fy_id, FinancialYear.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_current_for_company(self, company_id: uuid.UUID) -> FinancialYear | None:
        result = await self.db.execute(
            select(FinancialYear).where(
                FinancialYear.company_id == company_id, FinancialYear.is_current.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def get_for_date(self, company_id: uuid.UUID, on_date: date) -> FinancialYear | None:
        result = await self.db.execute(
            select(FinancialYear).where(
                FinancialYear.company_id == company_id,
                FinancialYear.start_date <= on_date,
                FinancialYear.end_date >= on_date,
            )
        )
        return result.scalar_one_or_none()

    async def unset_current_for_company(self, company_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(FinancialYear).where(
                FinancialYear.company_id == company_id, FinancialYear.is_current.is_(True)
            )
        )
        for fy in result.scalars().all():
            fy.is_current = False
        await self.db.flush()

    async def list_for_company(
        self, company_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[FinancialYear], int]:
        base = select(FinancialYear).where(FinancialYear.company_id == company_id)
        count_result = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            base.order_by(FinancialYear.start_date.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
