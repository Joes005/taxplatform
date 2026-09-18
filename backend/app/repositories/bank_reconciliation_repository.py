import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_reconciliation import BankReconciliation


class BankReconciliationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, reconciliation: BankReconciliation) -> BankReconciliation:
        self.db.add(reconciliation)
        await self.db.flush()
        return reconciliation

    async def get_by_id_for_company(
        self, reconciliation_id: uuid.UUID, company_id: uuid.UUID
    ) -> BankReconciliation | None:
        result = await self.db.execute(
            select(BankReconciliation).where(
                BankReconciliation.id == reconciliation_id, BankReconciliation.company_id == company_id
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
    ) -> tuple[list[BankReconciliation], int]:
        query = select(BankReconciliation).where(BankReconciliation.company_id == company_id)
        if bank_account_id is not None:
            query = query.where(BankReconciliation.bank_account_id == bank_account_id)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(BankReconciliation.period_start.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_open_for_account_period(
        self, company_id: uuid.UUID, bank_account_id: uuid.UUID, period_start, period_end
    ) -> BankReconciliation | None:
        from app.models.bank_enums import BankReconciliationStatus

        result = await self.db.execute(
            select(BankReconciliation).where(
                BankReconciliation.company_id == company_id,
                BankReconciliation.bank_account_id == bank_account_id,
                BankReconciliation.period_start == period_start,
                BankReconciliation.period_end == period_end,
                BankReconciliation.status.notin_(
                    [BankReconciliationStatus.CANCELLED, BankReconciliationStatus.LOCKED]
                ),
            )
        )
        return result.scalar_one_or_none()
