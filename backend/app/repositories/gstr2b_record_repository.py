import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gstr2b_record import GSTR2BRecord


class GSTR2BRecordRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id_for_company(
        self, record_id: uuid.UUID, company_id: uuid.UUID
    ) -> GSTR2BRecord | None:
        result = await self.db.execute(
            select(GSTR2BRecord).where(
                GSTR2BRecord.id == record_id, GSTR2BRecord.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        return_period_id: uuid.UUID | None = None,
        supplier_gstin: str | None = None,
        invoice_number: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[GSTR2BRecord], int]:
        query = select(GSTR2BRecord).where(GSTR2BRecord.company_id == company_id)
        if return_period_id is not None:
            query = query.where(GSTR2BRecord.return_period_id == return_period_id)
        if supplier_gstin:
            query = query.where(GSTR2BRecord.supplier_gstin == supplier_gstin.upper())
        if invoice_number:
            query = query.where(GSTR2BRecord.invoice_number.ilike(f"%{invoice_number}%"))

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.order_by(GSTR2BRecord.invoice_date.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_all_for_period(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> list[GSTR2BRecord]:
        result = await self.db.execute(
            select(GSTR2BRecord).where(
                GSTR2BRecord.company_id == company_id,
                GSTR2BRecord.return_period_id == return_period_id,
            )
        )
        return list(result.scalars().all())
