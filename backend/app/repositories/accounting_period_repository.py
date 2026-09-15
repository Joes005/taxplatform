import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_period import AccountingPeriod


class AccountingPeriodRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, period: AccountingPeriod) -> AccountingPeriod:
        self.db.add(period)
        await self.db.flush()
        return period

    async def get_by_id_for_company(
        self, period_id: uuid.UUID, company_id: uuid.UUID
    ) -> AccountingPeriod | None:
        result = await self.db.execute(
            select(AccountingPeriod).where(
                AccountingPeriod.id == period_id, AccountingPeriod.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_for_date(self, company_id: uuid.UUID, on_date: date) -> AccountingPeriod | None:
        result = await self.db.execute(
            select(AccountingPeriod).where(
                AccountingPeriod.company_id == company_id,
                AccountingPeriod.start_date <= on_date,
                AccountingPeriod.end_date >= on_date,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        financial_year_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AccountingPeriod], int]:
        base = select(AccountingPeriod).where(AccountingPeriod.company_id == company_id)
        if financial_year_id is not None:
            base = base.where(AccountingPeriod.financial_year_id == financial_year_id)
        count_result = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            base.order_by(AccountingPeriod.start_date.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
