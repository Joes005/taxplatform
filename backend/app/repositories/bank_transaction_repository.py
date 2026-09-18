import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_enums import BankTransactionReconciliationStatus
from app.models.bank_transaction import BankTransaction


class BankTransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, transaction: BankTransaction) -> BankTransaction:
        self.db.add(transaction)
        await self.db.flush()
        return transaction

    async def get_by_id_for_company(
        self, transaction_id: uuid.UUID, company_id: uuid.UUID
    ) -> BankTransaction | None:
        result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.id == transaction_id, BankTransaction.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_checksum(
        self, company_id: uuid.UUID, bank_account_id: uuid.UUID, checksum: str
    ) -> BankTransaction | None:
        result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.company_id == company_id,
                BankTransaction.bank_account_id == bank_account_id,
                BankTransaction.checksum == checksum,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_statement(self, bank_statement_id: uuid.UUID) -> list[BankTransaction]:
        result = await self.db.execute(
            select(BankTransaction).where(BankTransaction.bank_statement_id == bank_statement_id)
        )
        return list(result.scalars().all())

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        bank_account_id: uuid.UUID | None = None,
        bank_statement_id: uuid.UUID | None = None,
        reconciliation_status: BankTransactionReconciliationStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[BankTransaction], int]:
        query = select(BankTransaction).where(BankTransaction.company_id == company_id)
        if bank_account_id is not None:
            query = query.where(BankTransaction.bank_account_id == bank_account_id)
        if bank_statement_id is not None:
            query = query.where(BankTransaction.bank_statement_id == bank_statement_id)
        if reconciliation_status is not None:
            query = query.where(BankTransaction.reconciliation_status == reconciliation_status)
        if date_from is not None:
            query = query.where(BankTransaction.transaction_date >= date_from)
        if date_to is not None:
            query = query.where(BankTransaction.transaction_date <= date_to)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                (BankTransaction.description.ilike(pattern))
                | (BankTransaction.reference_number.ilike(pattern))
            )

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(BankTransaction.transaction_date.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def sum_debits_credits_for_statement(
        self, bank_statement_id: uuid.UUID
    ) -> tuple[Decimal, Decimal]:
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(BankTransaction.debit_amount), 0),
                func.coalesce(func.sum(BankTransaction.credit_amount), 0),
            ).where(BankTransaction.bank_statement_id == bank_statement_id)
        )
        debit, credit = result.one()
        return Decimal(debit), Decimal(credit)

    async def list_unmatched_for_account(
        self, company_id: uuid.UUID, bank_account_id: uuid.UUID, *, period_start: date, period_end: date
    ) -> list[BankTransaction]:
        result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.company_id == company_id,
                BankTransaction.bank_account_id == bank_account_id,
                BankTransaction.transaction_date >= period_start,
                BankTransaction.transaction_date <= period_end,
                BankTransaction.reconciliation_status.in_(
                    [
                        BankTransactionReconciliationStatus.UNMATCHED,
                        BankTransactionReconciliationStatus.MATCH_SUGGESTED,
                        BankTransactionReconciliationStatus.REVIEW_REQUIRED,
                        BankTransactionReconciliationStatus.PARTIALLY_MATCHED,
                    ]
                ),
            )
        )
        return list(result.scalars().all())

    async def list_for_account_period(
        self, company_id: uuid.UUID, bank_account_id: uuid.UUID, *, period_start: date, period_end: date
    ) -> list[BankTransaction]:
        result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.company_id == company_id,
                BankTransaction.bank_account_id == bank_account_id,
                BankTransaction.transaction_date >= period_start,
                BankTransaction.transaction_date <= period_end,
            )
        )
        return list(result.scalars().all())
