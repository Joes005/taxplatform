import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting_enums import NoteType, TransactionStatus
from app.models.credit_note import CreditNote
from app.models.debit_note import DebitNote
from app.models.product_service import ProductService
from app.models.sales_invoice import SalesInvoice


class GSTR1Repository:
    """Read-only queries over Phase 3 accounting data for GSTR-1
    preparation. Never writes to SalesInvoice/CreditNote/DebitNote — GST
    preparation must not mutate source accounting records (PHASE4 section
    64)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_sales_invoices(
        self,
        company_id: uuid.UUID,
        period_start: date,
        period_end: date,
        *,
        statuses: tuple[TransactionStatus, ...] = (TransactionStatus.POSTED,),
    ) -> list[SalesInvoice]:
        result = await self.db.execute(
            select(SalesInvoice)
            .options(selectinload(SalesInvoice.items), selectinload(SalesInvoice.customer))
            .where(
                SalesInvoice.company_id == company_id,
                SalesInvoice.invoice_date >= period_start,
                SalesInvoice.invoice_date <= period_end,
                SalesInvoice.status.in_(statuses),
            )
            .order_by(SalesInvoice.invoice_date.asc())
        )
        return list(result.unique().scalars().all())

    async def list_notes(
        self,
        model: type[CreditNote] | type[DebitNote],
        company_id: uuid.UUID,
        period_start: date,
        period_end: date,
        *,
        statuses: tuple[TransactionStatus, ...] = (TransactionStatus.POSTED,),
    ) -> list[CreditNote] | list[DebitNote]:
        date_field = model.credit_note_date if model is CreditNote else model.debit_note_date
        result = await self.db.execute(
            select(model)
            .options(selectinload(model.items), selectinload(model.customer))
            .where(
                model.company_id == company_id,
                model.note_type == NoteType.SALES,
                date_field >= period_start,
                date_field <= period_end,
                model.status.in_(statuses),
            )
            .order_by(date_field.asc())
        )
        return list(result.unique().scalars().all())

    async def get_products_by_ids(
        self, company_id: uuid.UUID, product_ids: set[uuid.UUID]
    ) -> dict[uuid.UUID, ProductService]:
        if not product_ids:
            return {}
        result = await self.db.execute(
            select(ProductService).where(
                ProductService.company_id == company_id, ProductService.id.in_(product_ids)
            )
        )
        return {p.id: p for p in result.scalars().all()}

    async def get_invoice_numbers_by_ids(
        self, company_id: uuid.UUID, invoice_ids: set[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        if not invoice_ids:
            return {}
        result = await self.db.execute(
            select(SalesInvoice.id, SalesInvoice.invoice_number).where(
                SalesInvoice.company_id == company_id, SalesInvoice.id.in_(invoice_ids)
            )
        )
        return {row.id: row.invoice_number for row in result.all()}
