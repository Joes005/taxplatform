import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_challan import TDSChallan, TDSChallanAllocation


class TDSChallanRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, challan: TDSChallan) -> TDSChallan:
        self.db.add(challan)
        await self.db.flush()
        return challan

    async def get_by_id_for_company(
        self, challan_id: uuid.UUID, company_id: uuid.UUID
    ) -> TDSChallan | None:
        result = await self.db.execute(
            select(TDSChallan).where(TDSChallan.id == challan_id, TDSChallan.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        financial_year_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[TDSChallan], int]:
        query = select(TDSChallan).where(TDSChallan.company_id == company_id)
        if financial_year_id is not None:
            query = query.where(TDSChallan.financial_year_id == financial_year_id)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.order_by(TDSChallan.challan_date.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_active_for_fy(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> list[TDSChallan]:
        from app.models.tds_enums import TDSChallanStatus

        result = await self.db.execute(
            select(TDSChallan).where(
                TDSChallan.company_id == company_id,
                TDSChallan.financial_year_id == financial_year_id,
                TDSChallan.status != TDSChallanStatus.CANCELLED,
            )
        )
        return list(result.scalars().all())

    async def sum_allocated(self, challan_id: uuid.UUID) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(TDSChallanAllocation.allocated_amount), 0)).where(
                TDSChallanAllocation.challan_id == challan_id
            )
        )
        return Decimal(result.scalar_one())

    async def sum_allocated_for_transaction(self, tds_transaction_id: uuid.UUID) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(TDSChallanAllocation.allocated_amount), 0)).where(
                TDSChallanAllocation.tds_transaction_id == tds_transaction_id
            )
        )
        return Decimal(result.scalar_one())

    async def create_allocation(self, allocation: TDSChallanAllocation) -> TDSChallanAllocation:
        self.db.add(allocation)
        await self.db.flush()
        return allocation

    async def list_allocations_for_challan(self, challan_id: uuid.UUID) -> list[TDSChallanAllocation]:
        result = await self.db.execute(
            select(TDSChallanAllocation).where(TDSChallanAllocation.challan_id == challan_id)
        )
        return list(result.scalars().all())
