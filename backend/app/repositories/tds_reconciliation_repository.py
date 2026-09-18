import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_reconciliation import TDSPaymentReconciliation


class TDSReconciliationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def clear_for_financial_year(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(TDSPaymentReconciliation).where(
                TDSPaymentReconciliation.company_id == company_id,
                TDSPaymentReconciliation.financial_year_id == financial_year_id,
            )
        )

    async def create(self, row: TDSPaymentReconciliation) -> TDSPaymentReconciliation:
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        financial_year_id: uuid.UUID | None = None,
        status=None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[TDSPaymentReconciliation], int]:
        query = select(TDSPaymentReconciliation).where(TDSPaymentReconciliation.company_id == company_id)
        if financial_year_id is not None:
            query = query.where(TDSPaymentReconciliation.financial_year_id == financial_year_id)
        if status is not None:
            query = query.where(TDSPaymentReconciliation.status == status)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.order_by(TDSPaymentReconciliation.run_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
