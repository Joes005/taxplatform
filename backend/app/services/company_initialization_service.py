import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.accounting_enums import BalanceType, FinancialYearStatus, LedgerType
from app.core.permissions import RoleCode
from app.models.company import Company
from app.models.financial_year import FinancialYear
from app.models.ledger import Ledger
from app.models.membership import CompanyMembership, MembershipStatus
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.ledger_repository import LedgerRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.company import CompanyCreate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

ZERO = Decimal("0.00")

DEFAULT_CORE_LEDGERS: list[tuple[str, LedgerType, BalanceType]] = [
    # Cash & Bank
    ("Cash", LedgerType.CASH, BalanceType.DEBIT),
    ("Bank Account", LedgerType.BANK, BalanceType.DEBIT),
    # Receivables & Payables
    ("Accounts Receivable", LedgerType.RECEIVABLE, BalanceType.DEBIT),
    ("Accounts Payable", LedgerType.PAYABLE, BalanceType.CREDIT),
    # Sales & Purchases (Income & Expense)
    ("Sales Account", LedgerType.INCOME, BalanceType.CREDIT),
    ("Purchase Account", LedgerType.EXPENSE, BalanceType.DEBIT),
    ("Round Off", LedgerType.EXPENSE, BalanceType.DEBIT),
    # Input GST (Tax / Asset)
    ("Input CGST", LedgerType.TAX, BalanceType.DEBIT),
    ("Input SGST", LedgerType.TAX, BalanceType.DEBIT),
    ("Input IGST", LedgerType.TAX, BalanceType.DEBIT),
    # Output GST (Tax / Liability)
    ("Output CGST", LedgerType.TAX, BalanceType.CREDIT),
    ("Output SGST", LedgerType.TAX, BalanceType.CREDIT),
    ("Output IGST", LedgerType.TAX, BalanceType.CREDIT),
]


def compute_default_financial_year(start_override: date | None = None) -> tuple[str, date, date]:
    """Compute standard Indian financial year (April 1 to March 31)."""
    ref_date = start_override or date.today()
    if ref_date.month >= 4:
        start_year = ref_date.year
    else:
        start_year = ref_date.year - 1
    end_year = start_year + 1
    fy_start = date(start_year, 4, 1)
    fy_end = date(end_year, 3, 31)
    short_end = str(end_year)[-2:]
    fy_name = f"FY {start_year}-{short_end}"
    return fy_name, fy_start, fy_end


class CompanyInitializationService:
    """Orchestrates company onboarding, creator membership assignment,
    default Financial Year creation, and default Chart of Accounts seeding.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.companies = CompanyRepository(db)
        self.memberships = MembershipRepository(db)
        self.roles = RoleRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.ledgers = LedgerRepository(db)
        self.audit = AuditService(db)

    async def initialize_new_company(
        self, payload: CompanyCreate, current_user: User, meta: RequestMeta
    ) -> Company:
        # 1. Create company record
        company = Company(**payload.model_dump())
        await self.companies.create(company)

        # 2. Assign creator as COMPANY_ADMIN membership
        admin_role = await self.roles.get_by_code(RoleCode.COMPANY_ADMIN.value)
        if admin_role is None:
            raise AppException("Default admin role not configured")

        membership = CompanyMembership(
            user_id=current_user.id,
            company_id=company.id,
            role_id=admin_role.id,
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
        )
        await self.memberships.create(membership)

        # 3. Initialize default Financial Year
        fy_name, fy_start, fy_end = compute_default_financial_year(payload.financial_year_start)
        existing_fy = await self.financial_years.get_current_for_company(company.id)
        if not existing_fy:
            fy = FinancialYear(
                company_id=company.id,
                name=fy_name,
                start_date=fy_start,
                end_date=fy_end,
                is_current=True,
                status=FinancialYearStatus.OPEN,
            )
            await self.financial_years.create(fy)

        # 4. Seed default Core Ledgers (Chart of Accounts)
        for name, l_type, bal_type in DEFAULT_CORE_LEDGERS:
            query = select(Ledger.id).where(Ledger.company_id == company.id, Ledger.name == name)
            exists = (await self.db.execute(query)).scalar_one_or_none()
            if not exists:
                ledger = Ledger(
                    company_id=company.id,
                    name=name,
                    ledger_type=l_type,
                    opening_balance=ZERO,
                    opening_balance_type=bal_type,
                    is_active=True,
                )
                await self.ledgers.create(ledger)

        # 5. Audit Logging
        await self.audit.log(
            action=AuditAction.COMPANY_CREATE,
            user_id=current_user.id,
            company_id=company.id,
            resource_type="company",
            resource_id=str(company.id),
            description=f"Company '{company.legal_name}' onboarded with admin membership, default FY ({fy_name}), and core chart of accounts",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        return company
