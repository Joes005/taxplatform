import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_review_note import TDSReviewNote


class TDSReviewNoteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, note: TDSReviewNote) -> TDSReviewNote:
        self.db.add(note)
        await self.db.flush()
        return note

    async def get_by_id_for_company(self, note_id: uuid.UUID, company_id: uuid.UUID) -> TDSReviewNote | None:
        result = await self.db.execute(
            select(TDSReviewNote).where(TDSReviewNote.id == note_id, TDSReviewNote.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_for_period(
        self,
        company_id: uuid.UUID,
        return_period_id: uuid.UUID,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> list[TDSReviewNote]:
        query = select(TDSReviewNote).where(
            TDSReviewNote.company_id == company_id, TDSReviewNote.return_period_id == return_period_id
        )
        if entity_type is not None:
            query = query.where(TDSReviewNote.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(TDSReviewNote.entity_id == entity_id)
        result = await self.db.execute(query.order_by(TDSReviewNote.created_at.desc()))
        return list(result.scalars().all())
