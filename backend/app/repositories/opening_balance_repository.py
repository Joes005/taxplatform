import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_enums import OpeningBalanceAccountType
from app.models.opening_balance import OpeningBalance


class OpeningBalanceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, ob: OpeningBalance) -> OpeningBalance:
        self.db.add(ob)
        await self.db.flush()
        return ob

    async def get_existing(
        self,
        *,
        company_id: uuid.UUID,
        financial_year_id: uuid.UUID,
        account_type: OpeningBalanceAccountType,
        account_id: uuid.UUID,
    ) -> OpeningBalance | None:
        result = await self.db.execute(
            select(OpeningBalance).where(
                OpeningBalance.company_id == company_id,
                OpeningBalance.financial_year_id == financial_year_id,
                OpeningBalance.account_type == account_type,
                OpeningBalance.account_id == account_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        financial_year_id: uuid.UUID | None = None,
        account_type: OpeningBalanceAccountType | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[OpeningBalance], int]:
        query = select(OpeningBalance).where(OpeningBalance.company_id == company_id)
        if financial_year_id is not None:
            query = query.where(OpeningBalance.financial_year_id == financial_year_id)
        if account_type is not None:
            query = query.where(OpeningBalance.account_type == account_type)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(query.offset(offset).limit(limit))
        return list(result.scalars().all()), total
