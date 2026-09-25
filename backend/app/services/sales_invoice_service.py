import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, DuplicateResourceError, NotFoundError, ValidationAppError
from app.models.accounting_enums import TransactionStatus
from app.models.sales_invoice import SalesInvoice, SalesInvoiceItem
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.sales_invoice_repository import SalesInvoiceRepository
from app.schemas.sales_invoice import SalesInvoiceCreate, SalesInvoiceUpdate
from app.services.accounting_calculation_service import AccountingCalculationService, LineItemInput
from app.services.accounting_guards import assert_date_in_financial_year, assert_period_open
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.invoice_posting_service import InvoicePostingService


class SalesInvoiceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SalesInvoiceRepository(db)
        self.customers = CustomerRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.audit = AuditService(db)
        self.posting_service = InvoicePostingService(db)

    async def _validate_references(
        self, company_id: uuid.UUID, customer_id: uuid.UUID, financial_year_id: uuid.UUID
    ):
        customer = await self.customers.get_by_id_for_company(customer_id, company_id)
        if customer is None:
            raise ValidationAppError("Customer not found in this company", code="MISSING_CUSTOMER")

        fy = await self.financial_years.get_by_id_for_company(financial_year_id, company_id)
        if fy is None:
            raise ValidationAppError(
                "Financial year not found in this company", code="INVALID_FINANCIAL_YEAR"
            )
        return customer, fy

    def _build_items(self, items_payload) -> tuple[list[SalesInvoiceItem], list[LineItemInput]]:
        line_inputs = [
            LineItemInput(
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount=i.discount,
                cgst_rate=i.cgst_rate,
                sgst_rate=i.sgst_rate,
                igst_rate=i.igst_rate,
                cess_rate=i.cess_rate,
            )
            for i in items_payload
        ]
        totals = AccountingCalculationService.calculate_document(line_inputs)

        items = []
        for payload_item, result in zip(items_payload, totals.line_results):
            items.append(
                SalesInvoiceItem(
                    product_service_id=payload_item.product_service_id,
                    description=payload_item.description,
                    quantity=payload_item.quantity,
                    unit=payload_item.unit,
                    unit_price=payload_item.unit_price,
                    discount=payload_item.discount,
                    taxable_value=result.taxable_value,
                    tax_rate=result.tax_rate,
                    cgst_rate=payload_item.cgst_rate,
                    sgst_rate=payload_item.sgst_rate,
                    igst_rate=payload_item.igst_rate,
                    cess_rate=payload_item.cess_rate,
                    cgst_amount=result.cgst_amount,
                    sgst_amount=result.sgst_amount,
                    igst_amount=result.igst_amount,
                    cess_amount=result.cess_amount,
                    total_amount=result.total_amount,
                )
            )
        return items, totals

    async def create(
        self, company_id: uuid.UUID, payload: SalesInvoiceCreate, current_user: User, meta: RequestMeta
    ) -> SalesInvoice:
        _customer, fy = await self._validate_references(
            company_id, payload.customer_id, payload.financial_year_id
        )
        assert_date_in_financial_year(fy, payload.invoice_date)

        existing = await self.repo.find_duplicate(
            company_id=company_id,
            invoice_number=payload.invoice_number,
            invoice_date=payload.invoice_date,
            customer_id=payload.customer_id,
        )
        if existing is not None:
            await self.audit.log(
                action=AuditAction.DUPLICATE_DETECTED,
                user_id=current_user.id,
                company_id=company_id,
                resource_type="sales_invoice",
                resource_id=str(existing.id),
                description=f"Duplicate sales invoice attempt: {payload.invoice_number}",
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
            raise DuplicateResourceError(
                "An invoice with this number, date, and customer already exists",
                code="DUPLICATE_INVOICE",
                details={"existing_invoice_id": str(existing.id)},
            )

        items, totals = self._build_items(payload.items)

        invoice = SalesInvoice(
            company_id=company_id,
            financial_year_id=payload.financial_year_id,
            customer_id=payload.customer_id,
            invoice_number=payload.invoice_number,
            invoice_date=payload.invoice_date,
            place_of_supply=payload.place_of_supply,
            place_of_supply_state_code=payload.place_of_supply_state_code,
            export_type=payload.export_type,
            shipping_bill_number=payload.shipping_bill_number,
            shipping_bill_date=payload.shipping_bill_date,
            port_code=payload.port_code,
            subtotal=totals.subtotal,
            discount=totals.discount,
            taxable_amount=totals.taxable_amount,
            cgst_amount=totals.cgst_amount,
            sgst_amount=totals.sgst_amount,
            igst_amount=totals.igst_amount,
            cess_amount=totals.cess_amount,
            total_tax=totals.total_tax,
            grand_total=totals.grand_total,
            round_off=totals.round_off,
            status=TransactionStatus.DRAFT,
            source=payload.source,
            source_reference=payload.source_reference,
            items=items,
        )
        await self.repo.create(invoice)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="sales_invoice",
            resource_id=str(invoice.id),
            description=f"Sales invoice '{invoice.invoice_number}' created",
            metadata={"grand_total": str(invoice.grand_total)},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return invoice

    async def get(self, company_id: uuid.UUID, invoice_id: uuid.UUID) -> SalesInvoice:
        invoice = await self.repo.get_by_id_for_company(invoice_id, company_id)
        if invoice is None:
            raise NotFoundError("Sales invoice not found", code="SALES_INVOICE_NOT_FOUND")
        return invoice

    async def list(self, company_id: uuid.UUID, *, page: int, page_size: int, **filters):
        return await self.repo.list_filtered(
            company_id=company_id, offset=(page - 1) * page_size, limit=page_size, **filters
        )

    async def update(
        self,
        company_id: uuid.UUID,
        invoice_id: uuid.UUID,
        payload: SalesInvoiceUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> SalesInvoice:
        invoice = await self.get(company_id, invoice_id)
        if invoice.status != TransactionStatus.DRAFT:
            raise ConflictError(
                "Only a DRAFT invoice can be edited — posted invoices are permanent records",
                code="POSTED_TRANSACTION_IMMUTABLE",
            )

        updates = payload.model_dump(exclude_unset=True, exclude={"items"})

        customer_id = payload.customer_id or invoice.customer_id
        financial_year_id = invoice.financial_year_id
        if payload.customer_id is not None:
            await self._validate_references(company_id, customer_id, financial_year_id)

        invoice_date = payload.invoice_date or invoice.invoice_date
        if payload.invoice_date is not None:
            fy = await self.financial_years.get_by_id_for_company(financial_year_id, company_id)
            assert_date_in_financial_year(fy, invoice_date)

        for field, value in updates.items():
            setattr(invoice, field, value)

        if payload.items is not None:
            for old_item in list(invoice.items):
                invoice.items.remove(old_item)
                await self.db.delete(old_item)
            new_items, totals = self._build_items(payload.items)
            invoice.items.extend(new_items)
            invoice.subtotal = totals.subtotal
            invoice.discount = totals.discount
            invoice.taxable_amount = totals.taxable_amount
            invoice.cgst_amount = totals.cgst_amount
            invoice.sgst_amount = totals.sgst_amount
            invoice.igst_amount = totals.igst_amount
            invoice.cess_amount = totals.cess_amount
            invoice.total_tax = totals.total_tax
            invoice.grand_total = totals.grand_total
            invoice.round_off = totals.round_off

        await self.db.flush()
        await self.db.refresh(invoice, attribute_names=["updated_at"])

        await self.audit.log(
            action=AuditAction.ACCOUNTING_UPDATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="sales_invoice",
            resource_id=str(invoice.id),
            description=f"Sales invoice '{invoice.invoice_number}' updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return invoice

    async def post(
        self, company_id: uuid.UUID, invoice_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> SalesInvoice:
        invoice = await self.get(company_id, invoice_id)
        if invoice.status != TransactionStatus.DRAFT:
            raise ConflictError(
                f"Only a DRAFT invoice can be posted (current status: {invoice.status.value})",
                code="INVALID_STATUS_TRANSITION",
            )

        fy = await self.financial_years.get_by_id_for_company(invoice.financial_year_id, company_id)
        assert_date_in_financial_year(fy, invoice.invoice_date)
        await assert_period_open(self.db, company_id=company_id, on_date=invoice.invoice_date)

        # Create balanced journal entry atomically
        await self.posting_service.post_sales_invoice(company_id, invoice, current_user, meta)

        invoice.status = TransactionStatus.POSTED
        await self.db.flush()
        await self.db.refresh(invoice, attribute_names=["updated_at"])

        await self.audit.log(
            action=AuditAction.ACCOUNTING_POST,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="sales_invoice",
            resource_id=str(invoice.id),
            description=f"Sales invoice '{invoice.invoice_number}' posted",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return invoice

    async def cancel(
        self, company_id: uuid.UUID, invoice_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> SalesInvoice:
        invoice = await self.get(company_id, invoice_id)
        if invoice.status == TransactionStatus.CANCELLED:
            raise ConflictError("Invoice is already cancelled", code="ALREADY_CANCELLED")

        if invoice.status == TransactionStatus.POSTED:
            # Check period is open before reversing posted invoice
            await assert_period_open(self.db, company_id=company_id, on_date=invoice.invoice_date)
            await self.posting_service.cancel_sales_invoice_posting(company_id, invoice, current_user, meta)

        invoice.status = TransactionStatus.CANCELLED
        await self.db.flush()
        await self.db.refresh(invoice, attribute_names=["updated_at"])

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CANCEL,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="sales_invoice",
            resource_id=str(invoice.id),
            description=f"Sales invoice '{invoice.invoice_number}' cancelled",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return invoice
