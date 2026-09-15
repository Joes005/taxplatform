import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def get_by_id_for_company(
        self, payment_id: uuid.UUID, company_id: uuid.UUID
    ) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id, Payment.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        financial_year_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Payment], int]:
        query = select(Payment).where(Payment.company_id == company_id)
        if financial_year_id is not None:
            query = query.where(Payment.financial_year_id == financial_year_id)
        if date_from is not None:
            query = query.where(Payment.payment_date >= date_from)
        if date_to is not None:
            query = query.where(Payment.payment_date <= date_to)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(Payment.payment_date.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
