import uuid
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting_enums import TransactionStatus
from app.models.gst_enums import ITCCategory, ReconciliationStatus
from app.models.gst_reconciliation import GSTReconciliation, GSTReconciliationResult
from app.models.gstr2b_record import GSTR2BRecord
from app.models.purchase_invoice import PurchaseInvoice


class GSTReconciliationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_posted_purchase_invoices(
        self, company_id: uuid.UUID, period_start: date, period_end: date
    ) -> list[PurchaseInvoice]:
        result = await self.db.execute(
            select(PurchaseInvoice)
            .options(selectinload(PurchaseInvoice.vendor))
            .where(
                PurchaseInvoice.company_id == company_id,
                PurchaseInvoice.invoice_date >= period_start,
                PurchaseInvoice.invoice_date <= period_end,
                PurchaseInvoice.status == TransactionStatus.POSTED,
            )
        )
        return list(result.unique().scalars().all())

    async def list_gstr2b_records(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> list[GSTR2BRecord]:
        result = await self.db.execute(
            select(GSTR2BRecord).where(
                GSTR2BRecord.company_id == company_id,
                GSTR2BRecord.return_period_id == return_period_id,
            )
        )
        return list(result.scalars().all())

    async def create_run(self, run: GSTReconciliation) -> GSTReconciliation:
        self.db.add(run)
        await self.db.flush()
        return run

    async def get_latest_run(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> GSTReconciliation | None:
        result = await self.db.execute(
            select(GSTReconciliation)
            .where(
                GSTReconciliation.company_id == company_id,
                GSTReconciliation.return_period_id == return_period_id,
            )
            .order_by(GSTReconciliation.run_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def delete_previous_runs(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> None:
        """A rerun replaces the prior run's results entirely — cascade
        deletes GSTReconciliationResult rows with it (PHASE4 section 31)."""
        await self.db.execute(
            delete(GSTReconciliation).where(
                GSTReconciliation.company_id == company_id,
                GSTReconciliation.return_period_id == return_period_id,
            )
        )
        await self.db.flush()

    async def add_results(self, results: list[GSTReconciliationResult]) -> None:
        self.db.add_all(results)
        await self.db.flush()

    async def get_result_by_id_for_company(
        self, result_id: uuid.UUID, company_id: uuid.UUID
    ) -> GSTReconciliationResult | None:
        result = await self.db.execute(
            select(GSTReconciliationResult).where(
                GSTReconciliationResult.id == result_id,
                GSTReconciliationResult.company_id == company_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_results_for_run(
        self,
        reconciliation_id: uuid.UUID,
        *,
        status: ReconciliationStatus | None = None,
        itc_category: ITCCategory | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[GSTReconciliationResult], int]:
        query = select(GSTReconciliationResult).where(
            GSTReconciliationResult.reconciliation_id == reconciliation_id
        )
        if status is not None:
            query = query.where(GSTReconciliationResult.status == status)
        if itc_category is not None:
            query = query.where(GSTReconciliationResult.itc_category == itc_category)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(query.order_by(GSTReconciliationResult.created_at.asc()).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def summary_by_review_status(self, reconciliation_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(
                GSTReconciliationResult.itc_review_status,
                func.coalesce(func.sum(GSTReconciliationResult.books_cgst_amount), 0),
                func.coalesce(func.sum(GSTReconciliationResult.books_sgst_amount), 0),
                func.coalesce(func.sum(GSTReconciliationResult.books_igst_amount), 0),
                func.coalesce(func.sum(GSTReconciliationResult.books_cess_amount), 0),
            )
            .where(GSTReconciliationResult.reconciliation_id == reconciliation_id)
            .group_by(GSTReconciliationResult.itc_review_status)
        )
        return {
            row[0]: {
                "cgst_amount": row[1],
                "sgst_amount": row[2],
                "igst_amount": row[3],
                "cess_amount": row[4],
            }
            for row in result.all()
        }

    async def summary_for_run(self, reconciliation_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(
                GSTReconciliationResult.itc_category,
                func.count(),
                func.coalesce(func.sum(GSTReconciliationResult.books_taxable_value), 0),
                func.coalesce(func.sum(GSTReconciliationResult.books_cgst_amount), 0),
                func.coalesce(func.sum(GSTReconciliationResult.books_sgst_amount), 0),
                func.coalesce(func.sum(GSTReconciliationResult.books_igst_amount), 0),
                func.coalesce(func.sum(GSTReconciliationResult.books_cess_amount), 0),
            )
            .where(GSTReconciliationResult.reconciliation_id == reconciliation_id)
            .group_by(GSTReconciliationResult.itc_category)
        )
        return {
            row[0]: {
                "count": row[1],
                "taxable_value": row[2],
                "cgst_amount": row[3],
                "sgst_amount": row[4],
                "igst_amount": row[5],
                "cess_amount": row[6],
            }
            for row in result.all()
        }
