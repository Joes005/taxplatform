import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt


class ReceiptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, receipt: Receipt) -> Receipt:
        self.db.add(receipt)
        await self.db.flush()
        return receipt

    async def get_by_id_for_company(
        self, receipt_id: uuid.UUID, company_id: uuid.UUID
    ) -> Receipt | None:
        result = await self.db.execute(
            select(Receipt).where(Receipt.id == receipt_id, Receipt.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        financial_year_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Receipt], int]:
        query = select(Receipt).where(Receipt.company_id == company_id)
        if financial_year_id is not None:
            query = query.where(Receipt.financial_year_id == financial_year_id)
        if customer_id is not None:
            query = query.where(Receipt.customer_id == customer_id)
        if date_from is not None:
            query = query.where(Receipt.receipt_date >= date_from)
        if date_to is not None:
            query = query.where(Receipt.receipt_date <= date_to)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(Receipt.receipt_date.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
