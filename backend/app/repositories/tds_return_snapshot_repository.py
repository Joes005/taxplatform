import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_enums import TDSReturnType
from app.models.tds_return_snapshot import TDSReturnSnapshot


class TDSReturnSnapshotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, snapshot: TDSReturnSnapshot) -> TDSReturnSnapshot:
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def get_latest(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, return_type: TDSReturnType
    ) -> TDSReturnSnapshot | None:
        result = await self.db.execute(
            select(TDSReturnSnapshot)
            .where(
                TDSReturnSnapshot.company_id == company_id,
                TDSReturnSnapshot.return_period_id == return_period_id,
                TDSReturnSnapshot.return_type == return_type,
            )
            .order_by(TDSReturnSnapshot.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, return_type: TDSReturnType
    ) -> list[TDSReturnSnapshot]:
        result = await self.db.execute(
            select(TDSReturnSnapshot)
            .where(
                TDSReturnSnapshot.company_id == company_id,
                TDSReturnSnapshot.return_period_id == return_period_id,
                TDSReturnSnapshot.return_type == return_type,
            )
            .order_by(TDSReturnSnapshot.version.desc())
        )
        return list(result.scalars().all())
