import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting_enums import TransactionStatus
from app.models.sales_invoice import SalesInvoice


class SalesInvoiceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, invoice: SalesInvoice) -> SalesInvoice:
        self.db.add(invoice)
        await self.db.flush()
        return invoice

    async def get_by_id_for_company(
        self, invoice_id: uuid.UUID, company_id: uuid.UUID
    ) -> SalesInvoice | None:
        result = await self.db.execute(
            select(SalesInvoice)
            .options(selectinload(SalesInvoice.items), selectinload(SalesInvoice.customer))
            .where(SalesInvoice.id == invoice_id, SalesInvoice.company_id == company_id)
        )
        return result.unique().scalar_one_or_none()

    async def find_duplicate(
        self,
        *,
        company_id: uuid.UUID,
        invoice_number: str,
        invoice_date: date,
        customer_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> SalesInvoice | None:
        """§23 — duplicate = same company + invoice number + invoice date +
        customer, never invoice_number alone (different customers may
        legitimately reuse the same number)."""
        query = select(SalesInvoice).where(
            SalesInvoice.company_id == company_id,
            SalesInvoice.invoice_number == invoice_number,
            SalesInvoice.invoice_date == invoice_date,
            SalesInvoice.customer_id == customer_id,
            SalesInvoice.status != TransactionStatus.CANCELLED,
        )
        if exclude_id is not None:
            query = query.where(SalesInvoice.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        company_id: uuid.UUID,
        status: TransactionStatus | None = None,
        customer_id: uuid.UUID | None = None,
        financial_year_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[SalesInvoice], int]:
        query = select(SalesInvoice).where(SalesInvoice.company_id == company_id)

        if status is not None:
            query = query.where(SalesInvoice.status == status)
        if customer_id is not None:
            query = query.where(SalesInvoice.customer_id == customer_id)
        if financial_year_id is not None:
            query = query.where(SalesInvoice.financial_year_id == financial_year_id)
        if date_from is not None:
            query = query.where(SalesInvoice.invoice_date >= date_from)
        if date_to is not None:
            query = query.where(SalesInvoice.invoice_date <= date_to)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    SalesInvoice.invoice_number.ilike(pattern),
                    SalesInvoice.place_of_supply.ilike(pattern),
                )
            )

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.options(selectinload(SalesInvoice.items), selectinload(SalesInvoice.customer))
            .order_by(SalesInvoice.invoice_date.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.unique().scalars().all()), total
