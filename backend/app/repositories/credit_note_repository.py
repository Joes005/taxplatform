import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.credit_note import CreditNote


class CreditNoteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, note: CreditNote) -> CreditNote:
        self.db.add(note)
        await self.db.flush()
        return note

    async def get_by_id_for_company(
        self, note_id: uuid.UUID, company_id: uuid.UUID
    ) -> CreditNote | None:
        result = await self.db.execute(
            select(CreditNote)
            .options(selectinload(CreditNote.items))
            .where(CreditNote.id == note_id, CreditNote.company_id == company_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_for_company(
        self, company_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[CreditNote], int]:
        query = select(CreditNote).where(CreditNote.company_id == company_id)
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.options(selectinload(CreditNote.items))
            .order_by(CreditNote.credit_note_date.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.unique().scalars().all()), total
