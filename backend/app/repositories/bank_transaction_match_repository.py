import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_enums import BankMatchSourceType, BankMatchStatus
from app.models.bank_transaction_match import BankTransactionMatch


class BankTransactionMatchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, match: BankTransactionMatch) -> BankTransactionMatch:
        self.db.add(match)
        await self.db.flush()
        return match

    async def get_by_id_for_company(
        self, match_id: uuid.UUID, company_id: uuid.UUID
    ) -> BankTransactionMatch | None:
        result = await self.db.execute(
            select(BankTransactionMatch).where(
                BankTransactionMatch.id == match_id, BankTransactionMatch.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_active_for_bank_transaction(
        self, bank_transaction_id: uuid.UUID
    ) -> list[BankTransactionMatch]:
        result = await self.db.execute(
            select(BankTransactionMatch).where(
                BankTransactionMatch.bank_transaction_id == bank_transaction_id,
                BankTransactionMatch.status == BankMatchStatus.ACTIVE,
            )
        )
        return list(result.scalars().all())

    async def list_for_bank_transaction(self, bank_transaction_id: uuid.UUID) -> list[BankTransactionMatch]:
        result = await self.db.execute(
            select(BankTransactionMatch)
            .where(BankTransactionMatch.bank_transaction_id == bank_transaction_id)
            .order_by(BankTransactionMatch.matched_at.desc())
        )
        return list(result.scalars().all())

    async def sum_active_matched_amount(self, bank_transaction_id: uuid.UUID) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(BankTransactionMatch.matched_amount), 0)).where(
                BankTransactionMatch.bank_transaction_id == bank_transaction_id,
                BankTransactionMatch.status == BankMatchStatus.ACTIVE,
            )
        )
        return Decimal(result.scalar_one())

    async def sum_active_matched_amount_for_source(
        self, source_type: BankMatchSourceType, source_id: uuid.UUID
    ) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(BankTransactionMatch.matched_amount), 0)).where(
                BankTransactionMatch.source_type == source_type,
                BankTransactionMatch.source_id == source_id,
                BankTransactionMatch.status == BankMatchStatus.ACTIVE,
            )
        )
        return Decimal(result.scalar_one())

    async def has_active_match(self, source_type: BankMatchSourceType, source_id: uuid.UUID) -> bool:
        amount = await self.sum_active_matched_amount_for_source(source_type, source_id)
        return amount > 0
