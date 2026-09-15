import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.accounting_enums import NoteType, TransactionStatus
from app.models.debit_note import DebitNote, DebitNoteItem
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.debit_note_repository import DebitNoteRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.vendor_repository import VendorRepository
from app.schemas.debit_note import DebitNoteCreate
from app.services.accounting_calculation_service import AccountingCalculationService, LineItemInput
from app.services.accounting_guards import assert_date_in_financial_year, assert_period_open
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class DebitNoteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DebitNoteRepository(db)
        self.customers = CustomerRepository(db)
        self.vendors = VendorRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: DebitNoteCreate, current_user: User, meta: RequestMeta
    ) -> DebitNote:
        fy = await self.financial_years.get_by_id_for_company(payload.financial_year_id, company_id)
        if fy is None:
            raise ValidationAppError(
                "Financial year not found in this company", code="INVALID_FINANCIAL_YEAR"
            )
        assert_date_in_financial_year(fy, payload.debit_note_date)
        await assert_period_open(self.db, company_id=company_id, on_date=payload.debit_note_date)

        if payload.note_type == NoteType.SALES:
            customer = await self.customers.get_by_id_for_company(payload.customer_id, company_id)
            if customer is None:
                raise ValidationAppError("Customer not found in this company", code="MISSING_CUSTOMER")
        else:
            vendor = await self.vendors.get_by_id_for_company(payload.vendor_id, company_id)
            if vendor is None:
                raise ValidationAppError("Vendor not found in this company", code="MISSING_VENDOR")

        line_inputs = [
            LineItemInput(
                quantity=i.quantity,
                unit_price=i.unit_price,
                cgst_rate=i.cgst_rate,
                sgst_rate=i.sgst_rate,
                igst_rate=i.igst_rate,
                cess_rate=i.cess_rate,
            )
            for i in payload.items
        ]
        totals = AccountingCalculationService.calculate_document(line_inputs)

        items = [
            DebitNoteItem(
                product_service_id=p.product_service_id,
                description=p.description,
                quantity=p.quantity,
                unit_price=p.unit_price,
                taxable_value=r.taxable_value,
                tax_rate=r.tax_rate,
                cgst_rate=p.cgst_rate,
                sgst_rate=p.sgst_rate,
                igst_rate=p.igst_rate,
                cess_rate=p.cess_rate,
                cgst_amount=r.cgst_amount,
                sgst_amount=r.sgst_amount,
                igst_amount=r.igst_amount,
                cess_amount=r.cess_amount,
                total_amount=r.total_amount,
            )
            for p, r in zip(payload.items, totals.line_results)
        ]

        note = DebitNote(
            company_id=company_id,
            financial_year_id=payload.financial_year_id,
            note_type=payload.note_type,
            customer_id=payload.customer_id,
            vendor_id=payload.vendor_id,
            reference_sales_invoice_id=payload.reference_sales_invoice_id,
            reference_purchase_invoice_id=payload.reference_purchase_invoice_id,
            debit_note_number=payload.debit_note_number,
            debit_note_date=payload.debit_note_date,
            reason=payload.reason,
            taxable_amount=totals.taxable_amount,
            cgst_amount=totals.cgst_amount,
            sgst_amount=totals.sgst_amount,
            igst_amount=totals.igst_amount,
            cess_amount=totals.cess_amount,
            total_amount=totals.taxable_amount + totals.total_tax,
            status=TransactionStatus.POSTED,
            source=payload.source,
            source_reference=payload.source_reference,
            items=items,
        )
        await self.repo.create(note)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="debit_note",
            resource_id=str(note.id),
            description=f"Debit note '{note.debit_note_number}' created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return note

    async def get(self, company_id: uuid.UUID, note_id: uuid.UUID) -> DebitNote:
        note = await self.repo.get_by_id_for_company(note_id, company_id)
        if note is None:
            raise NotFoundError("Debit note not found", code="DEBIT_NOTE_NOT_FOUND")
        return note

    async def list(self, company_id: uuid.UUID, *, page: int, page_size: int):
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size
        )
