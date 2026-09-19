import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income_tax_loss import IncomeTaxLoss


class IncomeTaxLossRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxLoss) -> IncomeTaxLoss:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(self, entity_id: uuid.UUID, company_id: uuid.UUID) -> IncomeTaxLoss | None:
        result = await self.db.execute(
            select(IncomeTaxLoss).where(IncomeTaxLoss.id == entity_id, IncomeTaxLoss.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_for_origin_fy(
        self, company_id: uuid.UUID, origin_financial_year_id: uuid.UUID
    ) -> list[IncomeTaxLoss]:
        result = await self.db.execute(
            select(IncomeTaxLoss).where(
                IncomeTaxLoss.company_id == company_id,
                IncomeTaxLoss.origin_financial_year_id == origin_financial_year_id,
            )
        )
        return list(result.scalars().all())

    async def list_for_company(self, company_id: uuid.UUID) -> list[IncomeTaxLoss]:
        result = await self.db.execute(
            select(IncomeTaxLoss)
            .where(IncomeTaxLoss.company_id == company_id)
            .order_by(IncomeTaxLoss.created_at.asc())
        )
        return list(result.scalars().all())
