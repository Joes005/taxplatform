import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gst_profile import GSTProfile


class GSTProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, profile: GSTProfile) -> GSTProfile:
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_for_company(self, company_id: uuid.UUID) -> GSTProfile | None:
        result = await self.db.execute(
            select(GSTProfile).where(GSTProfile.company_id == company_id)
        )
        return result.scalar_one_or_none()
