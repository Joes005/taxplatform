import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_enums import TDSQuarter
from app.models.tds_return_period import TDSReturnPeriod


class TDSReturnPeriodRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, period: TDSReturnPeriod) -> TDSReturnPeriod:
        self.db.add(period)
        await self.db.flush()
        return period

    async def get_by_id_for_company(
        self, period_id: uuid.UUID, company_id: uuid.UUID
    ) -> TDSReturnPeriod | None:
        result = await self.db.execute(
            select(TDSReturnPeriod).where(
                TDSReturnPeriod.id == period_id, TDSReturnPeriod.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_quarter_for_company(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID, quarter: TDSQuarter
    ) -> TDSReturnPeriod | None:
        result = await self.db.execute(
            select(TDSReturnPeriod).where(
                TDSReturnPeriod.company_id == company_id,
                TDSReturnPeriod.financial_year_id == financial_year_id,
                TDSReturnPeriod.quarter == quarter,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self, company_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[TDSReturnPeriod], int]:
        query = select(TDSReturnPeriod).where(TDSReturnPeriod.company_id == company_id)
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(TDSReturnPeriod.period_start.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
