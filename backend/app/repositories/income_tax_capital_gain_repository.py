import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income_tax_capital_gain import IncomeTaxCapitalGain


class IncomeTaxCapitalGainRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxCapitalGain) -> IncomeTaxCapitalGain:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(self, entity_id: uuid.UUID, company_id: uuid.UUID) -> IncomeTaxCapitalGain | None:
        result = await self.db.execute(
            select(IncomeTaxCapitalGain).where(
                IncomeTaxCapitalGain.id == entity_id, IncomeTaxCapitalGain.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxCapitalGain]:
        result = await self.db.execute(
            select(IncomeTaxCapitalGain)
            .where(
                IncomeTaxCapitalGain.company_id == company_id,
                IncomeTaxCapitalGain.financial_year_id == financial_year_id,
            )
            .order_by(IncomeTaxCapitalGain.sale_date.asc())
        )
        return list(result.scalars().all())

    async def delete(self, entity: IncomeTaxCapitalGain) -> None:
        await self.db.delete(entity)
        await self.db.flush()
