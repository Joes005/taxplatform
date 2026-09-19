import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.itr_preparation import ITRPreparation


class ITRPreparationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, preparation: ITRPreparation) -> ITRPreparation:
        self.db.add(preparation)
        await self.db.flush()
        return preparation

    async def get_by_id_for_company(
        self, preparation_id: uuid.UUID, company_id: uuid.UUID
    ) -> ITRPreparation | None:
        result = await self.db.execute(
            select(ITRPreparation).where(
                ITRPreparation.id == preparation_id, ITRPreparation.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_for_computation(
        self, company_id: uuid.UUID, tax_computation_id: uuid.UUID
    ) -> ITRPreparation | None:
        result = await self.db.execute(
            select(ITRPreparation).where(
                ITRPreparation.company_id == company_id,
                ITRPreparation.tax_computation_id == tax_computation_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self, company_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[ITRPreparation], int]:
        query = select(ITRPreparation).where(ITRPreparation.company_id == company_id)
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(ITRPreparation.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
