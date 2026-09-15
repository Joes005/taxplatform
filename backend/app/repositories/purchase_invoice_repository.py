import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting_enums import TransactionStatus
from app.models.purchase_invoice import PurchaseInvoice


class PurchaseInvoiceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, invoice: PurchaseInvoice) -> PurchaseInvoice:
        self.db.add(invoice)
        await self.db.flush()
        return invoice

    async def get_by_id_for_company(
        self, invoice_id: uuid.UUID, company_id: uuid.UUID
    ) -> PurchaseInvoice | None:
        result = await self.db.execute(
            select(PurchaseInvoice)
            .options(selectinload(PurchaseInvoice.items), selectinload(PurchaseInvoice.vendor))
            .where(PurchaseInvoice.id == invoice_id, PurchaseInvoice.company_id == company_id)
        )
        return result.unique().scalar_one_or_none()

    async def find_duplicate(
        self,
        *,
        company_id: uuid.UUID,
        invoice_number: str,
        invoice_date: date,
        vendor_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> PurchaseInvoice | None:
        query = select(PurchaseInvoice).where(
            PurchaseInvoice.company_id == company_id,
            PurchaseInvoice.invoice_number == invoice_number,
            PurchaseInvoice.invoice_date == invoice_date,
            PurchaseInvoice.vendor_id == vendor_id,
            PurchaseInvoice.status != TransactionStatus.CANCELLED,
        )
        if exclude_id is not None:
            query = query.where(PurchaseInvoice.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        company_id: uuid.UUID,
        status: TransactionStatus | None = None,
        vendor_id: uuid.UUID | None = None,
        financial_year_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PurchaseInvoice], int]:
        query = select(PurchaseInvoice).where(PurchaseInvoice.company_id == company_id)

        if status is not None:
            query = query.where(PurchaseInvoice.status == status)
        if vendor_id is not None:
            query = query.where(PurchaseInvoice.vendor_id == vendor_id)
        if financial_year_id is not None:
            query = query.where(PurchaseInvoice.financial_year_id == financial_year_id)
        if date_from is not None:
            query = query.where(PurchaseInvoice.invoice_date >= date_from)
        if date_to is not None:
            query = query.where(PurchaseInvoice.invoice_date <= date_to)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    PurchaseInvoice.invoice_number.ilike(pattern),
                    PurchaseInvoice.supplier_invoice_number.ilike(pattern),
                )
            )

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.options(selectinload(PurchaseInvoice.items), selectinload(PurchaseInvoice.vendor))
            .order_by(PurchaseInvoice.invoice_date.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.unique().scalars().all()), total
