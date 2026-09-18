from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_section import TDSSection


class TDSSectionRepository:
    """TDSSection is platform-wide reference data (no `company_id`) — every
    method here is unscoped by tenant on purpose."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, section: TDSSection) -> TDSSection:
        self.db.add(section)
        await self.db.flush()
        return section

    async def get_by_id(self, section_id) -> TDSSection | None:
        result = await self.db.execute(select(TDSSection).where(TDSSection.id == section_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, section_code: str) -> TDSSection | None:
        result = await self.db.execute(
            select(TDSSection).where(TDSSection.section_code == section_code)
        )
        return result.scalar_one_or_none()

    async def list_all(self, *, is_active: bool | None = None) -> list[TDSSection]:
        query = select(TDSSection)
        if is_active is not None:
            query = query.where(TDSSection.is_active == is_active)
        result = await self.db.execute(query.order_by(TDSSection.section_code.asc()))
        return list(result.scalars().all())
