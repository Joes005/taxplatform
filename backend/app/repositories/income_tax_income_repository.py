import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income_tax_income import (
    IncomeTaxExemptIncome,
    IncomeTaxHousePropertyIncome,
    IncomeTaxOtherIncome,
    IncomeTaxSalaryIncome,
)


class IncomeTaxSalaryIncomeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxSalaryIncome) -> IncomeTaxSalaryIncome:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(self, entity_id: uuid.UUID, company_id: uuid.UUID) -> IncomeTaxSalaryIncome | None:
        result = await self.db.execute(
            select(IncomeTaxSalaryIncome).where(
                IncomeTaxSalaryIncome.id == entity_id, IncomeTaxSalaryIncome.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxSalaryIncome]:
        result = await self.db.execute(
            select(IncomeTaxSalaryIncome).where(
                IncomeTaxSalaryIncome.company_id == company_id,
                IncomeTaxSalaryIncome.financial_year_id == financial_year_id,
            )
        )
        return list(result.scalars().all())

    async def delete(self, entity: IncomeTaxSalaryIncome) -> None:
        await self.db.delete(entity)
        await self.db.flush()


class IncomeTaxHousePropertyIncomeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxHousePropertyIncome) -> IncomeTaxHousePropertyIncome:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(
        self, entity_id: uuid.UUID, company_id: uuid.UUID
    ) -> IncomeTaxHousePropertyIncome | None:
        result = await self.db.execute(
            select(IncomeTaxHousePropertyIncome).where(
                IncomeTaxHousePropertyIncome.id == entity_id, IncomeTaxHousePropertyIncome.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_fy(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> list[IncomeTaxHousePropertyIncome]:
        result = await self.db.execute(
            select(IncomeTaxHousePropertyIncome).where(
                IncomeTaxHousePropertyIncome.company_id == company_id,
                IncomeTaxHousePropertyIncome.financial_year_id == financial_year_id,
            )
        )
        return list(result.scalars().all())

    async def delete(self, entity: IncomeTaxHousePropertyIncome) -> None:
        await self.db.delete(entity)
        await self.db.flush()


class IncomeTaxOtherIncomeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxOtherIncome) -> IncomeTaxOtherIncome:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(self, entity_id: uuid.UUID, company_id: uuid.UUID) -> IncomeTaxOtherIncome | None:
        result = await self.db.execute(
            select(IncomeTaxOtherIncome).where(
                IncomeTaxOtherIncome.id == entity_id, IncomeTaxOtherIncome.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxOtherIncome]:
        result = await self.db.execute(
            select(IncomeTaxOtherIncome).where(
                IncomeTaxOtherIncome.company_id == company_id,
                IncomeTaxOtherIncome.financial_year_id == financial_year_id,
            )
        )
        return list(result.scalars().all())

    async def delete(self, entity: IncomeTaxOtherIncome) -> None:
        await self.db.delete(entity)
        await self.db.flush()


class IncomeTaxExemptIncomeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxExemptIncome) -> IncomeTaxExemptIncome:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(self, entity_id: uuid.UUID, company_id: uuid.UUID) -> IncomeTaxExemptIncome | None:
        result = await self.db.execute(
            select(IncomeTaxExemptIncome).where(
                IncomeTaxExemptIncome.id == entity_id, IncomeTaxExemptIncome.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxExemptIncome]:
        result = await self.db.execute(
            select(IncomeTaxExemptIncome).where(
                IncomeTaxExemptIncome.company_id == company_id,
                IncomeTaxExemptIncome.financial_year_id == financial_year_id,
            )
        )
        return list(result.scalars().all())

    async def delete(self, entity: IncomeTaxExemptIncome) -> None:
        await self.db.delete(entity)
        await self.db.flush()
