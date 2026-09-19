import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income_tax_adjustment import IncomeTaxAdjustment


class IncomeTaxAdjustmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxAdjustment) -> IncomeTaxAdjustment:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(self, entity_id: uuid.UUID, company_id: uuid.UUID) -> IncomeTaxAdjustment | None:
        result = await self.db.execute(
            select(IncomeTaxAdjustment).where(
                IncomeTaxAdjustment.id == entity_id, IncomeTaxAdjustment.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxAdjustment]:
        result = await self.db.execute(
            select(IncomeTaxAdjustment).where(
                IncomeTaxAdjustment.company_id == company_id,
                IncomeTaxAdjustment.financial_year_id == financial_year_id,
            )
        )
        return list(result.scalars().all())

    async def delete(self, entity: IncomeTaxAdjustment) -> None:
        await self.db.delete(entity)
        await self.db.flush()
