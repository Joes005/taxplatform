import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.accounting_enums import PartyType
from app.models.payment import Payment
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.ledger_repository import LedgerRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.vendor_repository import VendorRepository
from app.schemas.payment import PaymentCreate
from app.services.accounting_guards import assert_date_in_financial_year, assert_period_open
from app.services.audit_service import AuditAction, AuditService
from decimal import Decimal
from sqlalchemy import func, select
from app.models.purchase_invoice import PurchaseInvoice
from app.services.auth_service import RequestMeta
from app.services.invoice_posting_service import InvoicePostingService


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PaymentRepository(db)
        self.ledgers = LedgerRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.customers = CustomerRepository(db)
        self.vendors = VendorRepository(db)
        self.posting = InvoicePostingService(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: PaymentCreate, current_user: User, meta: RequestMeta
    ) -> Payment:
        ledger = await self.ledgers.get_by_id_for_company(payload.ledger_id, company_id)
        if ledger is None:
            raise ValidationAppError("Ledger not found in this company", code="INVALID_LEDGER")

        fy = await self.financial_years.get_by_id_for_company(payload.financial_year_id, company_id)
        if fy is None:
            raise ValidationAppError(
                "Financial year not found in this company", code="INVALID_FINANCIAL_YEAR"
            )
        assert_date_in_financial_year(fy, payload.payment_date)
        await assert_period_open(self.db, company_id=company_id, on_date=payload.payment_date)

        if payload.party_type == PartyType.VENDOR and payload.party_id:
            vendor = await self.vendors.get_by_id_for_company(payload.party_id, company_id)
            if vendor is None:
                raise ValidationAppError("Vendor not found in this company", code="MISSING_VENDOR")
            if payload.reference_number:
                inv_res = await self.db.execute(
                    select(PurchaseInvoice).where(
                        PurchaseInvoice.company_id == company_id,
                        PurchaseInvoice.vendor_id == payload.party_id,
                        PurchaseInvoice.invoice_number == payload.reference_number,
                    )
                )
                matching_inv = inv_res.scalar_one_or_none()
                if matching_inv:
                    already_paid = (
                        await self.db.execute(
                            select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
                                Payment.company_id == company_id,
                                Payment.party_id == payload.party_id,
                                Payment.reference_number == payload.reference_number,
                            )
                        )
                    ).scalar_one()
                    remaining = matching_inv.grand_total - already_paid
                    if payload.amount > remaining:
                        raise ValidationAppError(
                            f"Payment amount {payload.amount} exceeds purchase invoice remaining balance of {remaining}",
                            code="INVOICE_OVERPAYMENT",
                        )
        elif payload.party_type == PartyType.CUSTOMER and payload.party_id:
            customer = await self.customers.get_by_id_for_company(payload.party_id, company_id)
            if customer is None:
                raise ValidationAppError("Customer not found in this company", code="MISSING_CUSTOMER")

        payment = Payment(company_id=company_id, **payload.model_dump())
        await self.repo.create(payment)

        await self.posting.post_payment(company_id, payment, current_user, meta)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="payment",
            resource_id=str(payment.id),
            description=f"Payment '{payment.payment_number}' recorded ({payment.amount})",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return payment

    async def get(self, company_id: uuid.UUID, payment_id: uuid.UUID) -> Payment:
        payment = await self.repo.get_by_id_for_company(payment_id, company_id)
        if payment is None:
            raise NotFoundError("Payment not found", code="PAYMENT_NOT_FOUND")
        return payment

    async def list(self, company_id: uuid.UUID, *, page: int, page_size: int, **filters):
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size, **filters
        )
