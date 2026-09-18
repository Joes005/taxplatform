import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_enums import TDSTransactionStatus
from app.models.tds_transaction import TDSTransaction


class TDSTransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, transaction: TDSTransaction) -> TDSTransaction:
        self.db.add(transaction)
        await self.db.flush()
        return transaction

    async def get_by_id_for_company(
        self, transaction_id: uuid.UUID, company_id: uuid.UUID
    ) -> TDSTransaction | None:
        result = await self.db.execute(
            select(TDSTransaction).where(
                TDSTransaction.id == transaction_id, TDSTransaction.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        deductee_id: uuid.UUID | None = None,
        tds_section_id: uuid.UUID | None = None,
        status: TDSTransactionStatus | None = None,
        financial_year_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[TDSTransaction], int]:
        query = select(TDSTransaction).where(TDSTransaction.company_id == company_id)
        if deductee_id is not None:
            query = query.where(TDSTransaction.deductee_id == deductee_id)
        if tds_section_id is not None:
            query = query.where(TDSTransaction.tds_section_id == tds_section_id)
        if status is not None:
            query = query.where(TDSTransaction.status == status)
        if financial_year_id is not None:
            query = query.where(TDSTransaction.financial_year_id == financial_year_id)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.order_by(TDSTransaction.transaction_date.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_for_period(
        self, company_id: uuid.UUID, *, period_start: date, period_end: date
    ) -> list[TDSTransaction]:
        result = await self.db.execute(
            select(TDSTransaction).where(
                TDSTransaction.company_id == company_id,
                TDSTransaction.transaction_date >= period_start,
                TDSTransaction.transaction_date <= period_end,
                TDSTransaction.status != TDSTransactionStatus.CANCELLED,
            )
        )
        return list(result.scalars().all())

    async def list_deducted_or_paid_for_fy(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> list[TDSTransaction]:
        result = await self.db.execute(
            select(TDSTransaction).where(
                TDSTransaction.company_id == company_id,
                TDSTransaction.financial_year_id == financial_year_id,
                TDSTransaction.status.in_(
                    [TDSTransactionStatus.DEDUCTED, TDSTransactionStatus.PAID]
                ),
            )
        )
        return list(result.scalars().all())

    async def sum_gross_amount_for_deductee_section_fy(
        self,
        company_id: uuid.UUID,
        *,
        deductee_id: uuid.UUID,
        tds_section_id: uuid.UUID,
        financial_year_id: uuid.UUID,
        exclude_transaction_id: uuid.UUID | None = None,
        as_of: date | None = None,
    ) -> Decimal:
        """Sum of gross amounts already recorded for this deductee under
        this section in this financial year — used to evaluate a section's
        *aggregate* annual threshold (PHASE5 section 11: e.g. 194Q's ₹50L
        aggregate). Cancelled transactions never count towards it."""
        query = select(func.coalesce(func.sum(TDSTransaction.gross_amount), 0)).where(
            TDSTransaction.company_id == company_id,
            TDSTransaction.deductee_id == deductee_id,
            TDSTransaction.tds_section_id == tds_section_id,
            TDSTransaction.financial_year_id == financial_year_id,
            TDSTransaction.status != TDSTransactionStatus.CANCELLED,
        )
        if exclude_transaction_id is not None:
            query = query.where(TDSTransaction.id != exclude_transaction_id)
        if as_of is not None:
            query = query.where(TDSTransaction.transaction_date < as_of)
        result = await self.db.execute(query)
        return Decimal(result.scalar_one())

    async def payable_summary(
        self, company_id: uuid.UUID, *, financial_year_id: uuid.UUID | None = None
    ) -> dict[str, Decimal]:
        query = select(
            func.coalesce(
                func.sum(TDSTransaction.tds_amount).filter(
                    TDSTransaction.status.in_(
                        [TDSTransactionStatus.DEDUCTED, TDSTransactionStatus.PAID]
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(TDSTransaction.tds_amount).filter(
                    TDSTransaction.status == TDSTransactionStatus.PAID
                ),
                0,
            ),
        ).where(TDSTransaction.company_id == company_id)
        if financial_year_id is not None:
            query = query.where(TDSTransaction.financial_year_id == financial_year_id)
        result = await self.db.execute(query)
        deducted, paid = result.one()
        deducted = Decimal(deducted)
        paid = Decimal(paid)
        return {"tds_deducted": deducted, "tds_paid": paid, "tds_outstanding": deducted - paid}
