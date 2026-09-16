import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gst_tax_rate import GSTTaxRate


class GSTTaxRateRepository:
    """Rates visible to a company are its own (`company_id == company_id`)
    plus the platform-wide defaults (`company_id IS NULL`) — never another
    company's rates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, rate: GSTTaxRate) -> GSTTaxRate:
        self.db.add(rate)
        await self.db.flush()
        return rate

    async def get_by_id_for_company(
        self, rate_id: uuid.UUID, company_id: uuid.UUID
    ) -> GSTTaxRate | None:
        result = await self.db.execute(
            select(GSTTaxRate).where(
                GSTTaxRate.id == rate_id,
                or_(GSTTaxRate.company_id == company_id, GSTTaxRate.company_id.is_(None)),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        is_active: bool | None = None,
        as_of: date | None = None,
    ) -> list[GSTTaxRate]:
        query = select(GSTTaxRate).where(
            or_(GSTTaxRate.company_id == company_id, GSTTaxRate.company_id.is_(None))
        )
        if is_active is not None:
            query = query.where(GSTTaxRate.is_active == is_active)
        if as_of is not None:
            query = query.where(
                GSTTaxRate.effective_from <= as_of,
                or_(GSTTaxRate.effective_to.is_(None), GSTTaxRate.effective_to >= as_of),
            )
        result = await self.db.execute(query.order_by(GSTTaxRate.rate.asc()))
        return list(result.scalars().all())
