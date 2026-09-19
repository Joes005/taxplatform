import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income_tax_profile import IncomeTaxProfile


class IncomeTaxProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, profile: IncomeTaxProfile) -> IncomeTaxProfile:
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_for_company(self, company_id: uuid.UUID) -> IncomeTaxProfile | None:
        result = await self.db.execute(
            select(IncomeTaxProfile).where(IncomeTaxProfile.company_id == company_id)
        )
        return result.scalar_one_or_none()
