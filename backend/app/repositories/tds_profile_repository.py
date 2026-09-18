import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_profile import TDSProfile


class TDSProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, profile: TDSProfile) -> TDSProfile:
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_for_company(self, company_id: uuid.UUID) -> TDSProfile | None:
        result = await self.db.execute(
            select(TDSProfile).where(TDSProfile.company_id == company_id)
        )
        return result.scalar_one_or_none()
