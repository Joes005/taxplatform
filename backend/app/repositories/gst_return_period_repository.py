import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gst_return_period import GSTReturnPeriod


class GSTReturnPeriodRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, period: GSTReturnPeriod) -> GSTReturnPeriod:
        self.db.add(period)
        await self.db.flush()
        return period

    async def get_by_id_for_company(
        self, period_id: uuid.UUID, company_id: uuid.UUID
    ) -> GSTReturnPeriod | None:
        result = await self.db.execute(
            select(GSTReturnPeriod).where(
                GSTReturnPeriod.id == period_id, GSTReturnPeriod.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_year_month_for_company(
        self, company_id: uuid.UUID, year: int, month: int
    ) -> GSTReturnPeriod | None:
        result = await self.db.execute(
            select(GSTReturnPeriod).where(
                GSTReturnPeriod.company_id == company_id,
                GSTReturnPeriod.year == year,
                GSTReturnPeriod.month == month,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self, company_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[GSTReturnPeriod], int]:
        base = select(GSTReturnPeriod).where(GSTReturnPeriod.company_id == company_id)
        count_result = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            base.order_by(GSTReturnPeriod.year.desc(), GSTReturnPeriod.month.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total
