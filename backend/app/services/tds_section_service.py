from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_section import TDSSection
from app.repositories.tds_section_repository import TDSSectionRepository


class TDSSectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TDSSectionRepository(db)

    async def list(self, *, is_active: bool | None = None) -> list[TDSSection]:
        return await self.repo.list_all(is_active=is_active)
