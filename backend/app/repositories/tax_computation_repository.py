import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income_tax_enums import TaxComputationStatus
from app.models.tax_computation import TaxComputation, TaxComputationSnapshot


class TaxComputationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, computation: TaxComputation) -> TaxComputation:
        self.db.add(computation)
        await self.db.flush()
        return computation

    async def get_by_id_for_company(
        self, computation_id: uuid.UUID, company_id: uuid.UUID
    ) -> TaxComputation | None:
        result = await self.db.execute(
            select(TaxComputation).where(
                TaxComputation.id == computation_id, TaxComputation.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_active_for_fy(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> TaxComputation | None:
        result = await self.db.execute(
            select(TaxComputation)
            .where(
                TaxComputation.company_id == company_id,
                TaxComputation.financial_year_id == financial_year_id,
                TaxComputation.status != TaxComputationStatus.CANCELLED,
            )
            .order_by(TaxComputation.created_at.desc())
        )
        return result.scalars().first()

    async def list_for_company(
        self, company_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[TaxComputation], int]:
        query = select(TaxComputation).where(TaxComputation.company_id == company_id)
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(TaxComputation.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total


class TaxComputationSnapshotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, snapshot: TaxComputationSnapshot) -> TaxComputationSnapshot:
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def list_for_computation(self, tax_computation_id: uuid.UUID) -> list[TaxComputationSnapshot]:
        result = await self.db.execute(
            select(TaxComputationSnapshot)
            .where(TaxComputationSnapshot.tax_computation_id == tax_computation_id)
            .order_by(TaxComputationSnapshot.version.asc())
        )
        return list(result.scalars().all())

    async def next_version(self, tax_computation_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(TaxComputationSnapshot)
            .where(TaxComputationSnapshot.tax_computation_id == tax_computation_id)
        )
        return result.scalar_one() + 1
