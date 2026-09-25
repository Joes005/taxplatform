import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.accounting_enums import NoteType, TransactionStatus
from app.models.credit_note import CreditNote, CreditNoteItem
from app.models.user import User
from app.repositories.credit_note_repository import CreditNoteRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.vendor_repository import VendorRepository
from app.schemas.credit_note import CreditNoteCreate
from app.services.accounting_calculation_service import AccountingCalculationService, LineItemInput
from app.services.accounting_guards import assert_date_in_financial_year, assert_period_open
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


from sqlalchemy import select
from app.models.purchase_invoice import PurchaseInvoice
from app.models.sales_invoice import SalesInvoice
from app.services.invoice_posting_service import InvoicePostingService


class CreditNoteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CreditNoteRepository(db)
        self.customers = CustomerRepository(db)
        self.vendors = VendorRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.posting = InvoicePostingService(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: CreditNoteCreate, current_user: User, meta: RequestMeta
    ) -> CreditNote:
        fy = await self.financial_years.get_by_id_for_company(payload.financial_year_id, company_id)
        if fy is None:
            raise ValidationAppError(
                "Financial year not found in this company", code="INVALID_FINANCIAL_YEAR"
            )
        assert_date_in_financial_year(fy, payload.credit_note_date)
        await assert_period_open(self.db, company_id=company_id, on_date=payload.credit_note_date)

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
        total_note_amount = totals.taxable_amount + totals.total_tax

        if payload.note_type == NoteType.SALES:
            customer = await self.customers.get_by_id_for_company(payload.customer_id, company_id)
            if customer is None:
                raise ValidationAppError("Customer not found in this company", code="MISSING_CUSTOMER")
            if payload.reference_sales_invoice_id:
                inv_res = await self.db.execute(
                    select(SalesInvoice).where(
                        SalesInvoice.id == payload.reference_sales_invoice_id,
                        SalesInvoice.company_id == company_id,
                    )
                )
                ref_inv = inv_res.scalar_one_or_none()
                if ref_inv is None:
                    raise ValidationAppError(
                        "Referenced sales invoice not found in this company",
                        code="INVALID_INVOICE_REFERENCE",
                    )
                if ref_inv.customer_id != payload.customer_id:
                    raise ValidationAppError(
                        "Credit note customer must match referenced invoice customer",
                        code="CUSTOMER_MISMATCH",
                    )
                if total_note_amount > ref_inv.grand_total:
                    raise ValidationAppError(
                        f"Credit note amount ({total_note_amount}) cannot exceed referenced invoice amount ({ref_inv.grand_total})",
                        code="AMOUNT_EXCEEDS_INVOICE",
                    )
        else:
            vendor = await self.vendors.get_by_id_for_company(payload.vendor_id, company_id)
            if vendor is None:
                raise ValidationAppError("Vendor not found in this company", code="MISSING_VENDOR")
            if payload.reference_purchase_invoice_id:
                inv_res = await self.db.execute(
                    select(PurchaseInvoice).where(
                        PurchaseInvoice.id == payload.reference_purchase_invoice_id,
                        PurchaseInvoice.company_id == company_id,
                    )
                )
                ref_inv = inv_res.scalar_one_or_none()
                if ref_inv is None:
                    raise ValidationAppError(
                        "Referenced purchase invoice not found in this company",
                        code="INVALID_INVOICE_REFERENCE",
                    )
                if ref_inv.vendor_id != payload.vendor_id:
                    raise ValidationAppError(
                        "Credit note vendor must match referenced invoice vendor",
                        code="VENDOR_MISMATCH",
                    )
                if total_note_amount > ref_inv.grand_total:
                    raise ValidationAppError(
                        f"Credit note amount ({total_note_amount}) cannot exceed referenced invoice amount ({ref_inv.grand_total})",
                        code="AMOUNT_EXCEEDS_INVOICE",
                    )

        items = [
            CreditNoteItem(
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

        note = CreditNote(
            company_id=company_id,
            financial_year_id=payload.financial_year_id,
            note_type=payload.note_type,
            customer_id=payload.customer_id,
            vendor_id=payload.vendor_id,
            reference_sales_invoice_id=payload.reference_sales_invoice_id,
            reference_purchase_invoice_id=payload.reference_purchase_invoice_id,
            credit_note_number=payload.credit_note_number,
            credit_note_date=payload.credit_note_date,
            reason=payload.reason,
            taxable_amount=totals.taxable_amount,
            cgst_amount=totals.cgst_amount,
            sgst_amount=totals.sgst_amount,
            igst_amount=totals.igst_amount,
            cess_amount=totals.cess_amount,
            total_amount=total_note_amount,
            status=TransactionStatus.POSTED,
            source=payload.source,
            source_reference=payload.source_reference,
            items=items,
        )
        await self.repo.create(note)

        await self.posting.post_credit_note(company_id, note, current_user, meta)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="credit_note",
            resource_id=str(note.id),
            description=f"Credit note '{note.credit_note_number}' created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return note

    async def get(self, company_id: uuid.UUID, note_id: uuid.UUID) -> CreditNote:
        note = await self.repo.get_by_id_for_company(note_id, company_id)
        if note is None:
            raise NotFoundError("Credit note not found", code="CREDIT_NOTE_NOT_FOUND")
        return note

    async def list(self, company_id: uuid.UUID, *, page: int, page_size: int):
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size
        )
