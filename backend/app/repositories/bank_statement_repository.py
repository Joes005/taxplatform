import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_statement import BankStatement


class BankStatementRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, statement: BankStatement) -> BankStatement:
        self.db.add(statement)
        await self.db.flush()
        return statement

    async def get_by_id_for_company(
        self, statement_id: uuid.UUID, company_id: uuid.UUID
    ) -> BankStatement | None:
        result = await self.db.execute(
            select(BankStatement).where(
                BankStatement.id == statement_id, BankStatement.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        bank_account_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[BankStatement], int]:
        query = select(BankStatement).where(BankStatement.company_id == company_id)
        if bank_account_id is not None:
            query = query.where(BankStatement.bank_account_id == bank_account_id)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(BankStatement.period_start.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
