import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gst_enums import GSTReturnType
from app.models.gst_return_snapshot import GSTReturnSnapshot


class GSTReturnSnapshotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, snapshot: GSTReturnSnapshot) -> GSTReturnSnapshot:
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def get_latest(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, return_type: GSTReturnType
    ) -> GSTReturnSnapshot | None:
        result = await self.db.execute(
            select(GSTReturnSnapshot)
            .where(
                GSTReturnSnapshot.company_id == company_id,
                GSTReturnSnapshot.return_period_id == return_period_id,
                GSTReturnSnapshot.return_type == return_type,
            )
            .order_by(GSTReturnSnapshot.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_company(
        self, snapshot_id: uuid.UUID, company_id: uuid.UUID
    ) -> GSTReturnSnapshot | None:
        result = await self.db.execute(
            select(GSTReturnSnapshot).where(
                GSTReturnSnapshot.id == snapshot_id, GSTReturnSnapshot.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, return_type: GSTReturnType
    ) -> list[GSTReturnSnapshot]:
        result = await self.db.execute(
            select(GSTReturnSnapshot)
            .where(
                GSTReturnSnapshot.company_id == company_id,
                GSTReturnSnapshot.return_period_id == return_period_id,
                GSTReturnSnapshot.return_type == return_type,
            )
            .order_by(GSTReturnSnapshot.version.desc())
        )
        return list(result.scalars().all())
