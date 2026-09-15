import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting_enums import TransactionStatus
from app.models.journal_entry import JournalEntry


class JournalEntryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entry: JournalEntry) -> JournalEntry:
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_by_id_for_company(
        self, entry_id: uuid.UUID, company_id: uuid.UUID
    ) -> JournalEntry | None:
        result = await self.db.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(JournalEntry.id == entry_id, JournalEntry.company_id == company_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        financial_year_id: uuid.UUID | None = None,
        status: TransactionStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[JournalEntry], int]:
        query = select(JournalEntry).where(JournalEntry.company_id == company_id)
        if financial_year_id is not None:
            query = query.where(JournalEntry.financial_year_id == financial_year_id)
        if status is not None:
            query = query.where(JournalEntry.status == status)
        if date_from is not None:
            query = query.where(JournalEntry.journal_date >= date_from)
        if date_to is not None:
            query = query.where(JournalEntry.journal_date <= date_to)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.options(selectinload(JournalEntry.lines))
            .order_by(JournalEntry.journal_date.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.unique().scalars().all()), total
