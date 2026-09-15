import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.debit_note import DebitNote


class DebitNoteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, note: DebitNote) -> DebitNote:
        self.db.add(note)
        await self.db.flush()
        return note

    async def get_by_id_for_company(
        self, note_id: uuid.UUID, company_id: uuid.UUID
    ) -> DebitNote | None:
        result = await self.db.execute(
            select(DebitNote)
            .options(selectinload(DebitNote.items))
            .where(DebitNote.id == note_id, DebitNote.company_id == company_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_for_company(
        self, company_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[DebitNote], int]:
        query = select(DebitNote).where(DebitNote.company_id == company_id)
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.options(selectinload(DebitNote.items))
            .order_by(DebitNote.debit_note_date.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.unique().scalars().all()), total
