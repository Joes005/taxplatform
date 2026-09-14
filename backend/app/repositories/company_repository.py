import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


class CompanyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, company_id: uuid.UUID) -> Company | None:
        return await self.db.get(Company, company_id)

    async def create(self, company: Company) -> Company:
        self.db.add(company)
        await self.db.flush()
        return company

    async def list_by_ids(
        self, company_ids: list[uuid.UUID], *, offset: int = 0, limit: int = 20
    ) -> tuple[list[Company], int]:
        base_query = select(Company).where(Company.id.in_(company_ids))

        count_result = await self.db.execute(select(func.count()).select_from(base_query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            base_query.order_by(Company.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_all(self, *, offset: int = 0, limit: int = 20) -> tuple[list[Company], int]:
        count_result = await self.db.execute(select(func.count()).select_from(Company))
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Company).order_by(Company.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
