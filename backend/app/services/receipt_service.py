import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.receipt import Receipt
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.ledger_repository import LedgerRepository
from app.repositories.receipt_repository import ReceiptRepository
from app.schemas.receipt import ReceiptCreate
from app.services.accounting_guards import assert_date_in_financial_year, assert_period_open
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class ReceiptService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ReceiptRepository(db)
        self.ledgers = LedgerRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.customers = CustomerRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: ReceiptCreate, current_user: User, meta: RequestMeta
    ) -> Receipt:
        ledger = await self.ledgers.get_by_id_for_company(payload.ledger_id, company_id)
        if ledger is None:
            raise ValidationAppError("Ledger not found in this company", code="INVALID_LEDGER")

        customer = await self.customers.get_by_id_for_company(payload.customer_id, company_id)
        if customer is None:
            raise ValidationAppError("Customer not found in this company", code="MISSING_CUSTOMER")

        fy = await self.financial_years.get_by_id_for_company(payload.financial_year_id, company_id)
        if fy is None:
            raise ValidationAppError(
                "Financial year not found in this company", code="INVALID_FINANCIAL_YEAR"
            )
        assert_date_in_financial_year(fy, payload.receipt_date)
        await assert_period_open(self.db, company_id=company_id, on_date=payload.receipt_date)

        receipt = Receipt(company_id=company_id, **payload.model_dump())
        await self.repo.create(receipt)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="receipt",
            resource_id=str(receipt.id),
            description=f"Receipt '{receipt.receipt_number}' recorded ({receipt.amount})",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return receipt

    async def get(self, company_id: uuid.UUID, receipt_id: uuid.UUID) -> Receipt:
        receipt = await self.repo.get_by_id_for_company(receipt_id, company_id)
        if receipt is None:
            raise NotFoundError("Receipt not found", code="RECEIPT_NOT_FOUND")
        return receipt

    async def list(self, company_id: uuid.UUID, *, page: int, page_size: int, **filters):
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size, **filters
        )
