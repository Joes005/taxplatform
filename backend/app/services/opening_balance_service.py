import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ValidationAppError
from app.models.accounting_enums import OpeningBalanceAccountType
from app.models.opening_balance import OpeningBalance
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.ledger_repository import LedgerRepository
from app.repositories.opening_balance_repository import OpeningBalanceRepository
from app.repositories.vendor_repository import VendorRepository
from app.schemas.opening_balance import OpeningBalanceCreate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

_ACCOUNT_LABELS = {
    OpeningBalanceAccountType.LEDGER: "Ledger",
    OpeningBalanceAccountType.CUSTOMER: "Customer",
    OpeningBalanceAccountType.VENDOR: "Vendor",
}


class OpeningBalanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OpeningBalanceRepository(db)
        self.ledgers = LedgerRepository(db)
        self.customers = CustomerRepository(db)
        self.vendors = VendorRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def _validate_account(
        self, company_id: uuid.UUID, account_type: OpeningBalanceAccountType, account_id: uuid.UUID
    ) -> None:
        repo = {
            OpeningBalanceAccountType.LEDGER: self.ledgers,
            OpeningBalanceAccountType.CUSTOMER: self.customers,
            OpeningBalanceAccountType.VENDOR: self.vendors,
        }[account_type]
        entity = await repo.get_by_id_for_company(account_id, company_id)
        if entity is None:
            raise ValidationAppError(
                f"{_ACCOUNT_LABELS[account_type]} not found in this company",
                code="INVALID_OPENING_BALANCE_ACCOUNT",
            )

    async def create(
        self,
        company_id: uuid.UUID,
        payload: OpeningBalanceCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> OpeningBalance:
        fy = await self.financial_years.get_by_id_for_company(payload.financial_year_id, company_id)
        if fy is None:
            raise ValidationAppError(
                "Financial year not found in this company", code="INVALID_FINANCIAL_YEAR"
            )
        await self._validate_account(company_id, payload.account_type, payload.account_id)

        # §18 — never silently overwrite an existing opening balance; the
        # unique DB constraint backs this up structurally too.
        existing = await self.repo.get_existing(
            company_id=company_id,
            financial_year_id=payload.financial_year_id,
            account_type=payload.account_type,
            account_id=payload.account_id,
        )
        if existing is not None:
            raise ConflictError(
                "An opening balance already exists for this account and financial year — "
                "update it explicitly rather than creating a new one",
                code="OPENING_BALANCE_EXISTS",
            )

        ob = OpeningBalance(company_id=company_id, **payload.model_dump())
        await self.repo.create(ob)

        await self.audit.log(
            action=AuditAction.OPENING_BALANCE_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="opening_balance",
            resource_id=str(ob.id),
            description=f"Opening balance recorded for {payload.account_type.value} "
            f"{payload.account_id}: {payload.amount} {payload.balance_type.value}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return ob

    async def list(self, company_id: uuid.UUID, *, page: int, page_size: int, **filters):
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size, **filters
        )
