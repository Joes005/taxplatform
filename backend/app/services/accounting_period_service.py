import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.accounting_enums import PeriodStatus
from app.models.accounting_period import AccountingPeriod
from app.models.user import User
from app.repositories.accounting_period_repository import AccountingPeriodRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.schemas.accounting_period import AccountingPeriodCreate, AccountingPeriodUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class AccountingPeriodService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AccountingPeriodRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self,
        company_id: uuid.UUID,
        payload: AccountingPeriodCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> AccountingPeriod:
        fy = await self.financial_years.get_by_id_for_company(payload.financial_year_id, company_id)
        if fy is None:
            raise NotFoundError("Financial year not found", code="FINANCIAL_YEAR_NOT_FOUND")
        if not (fy.contains(payload.start_date) and fy.contains(payload.end_date)):
            raise ValidationAppError(
                f"Period dates must fall within financial year '{fy.name}'",
                code="INVALID_FINANCIAL_YEAR_DATE",
            )

        period = AccountingPeriod(company_id=company_id, **payload.model_dump())
        await self.repo.create(period)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="accounting_period",
            resource_id=str(period.id),
            description=f"Accounting period '{period.name}' created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return period

    async def get(self, company_id: uuid.UUID, period_id: uuid.UUID) -> AccountingPeriod:
        period = await self.repo.get_by_id_for_company(period_id, company_id)
        if period is None:
            raise NotFoundError("Accounting period not found", code="PERIOD_NOT_FOUND")
        return period

    async def list(
        self,
        company_id: uuid.UUID,
        *,
        financial_year_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AccountingPeriod], int]:
        return await self.repo.list_for_company(
            company_id,
            financial_year_id=financial_year_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def update_status(
        self,
        company_id: uuid.UUID,
        period_id: uuid.UUID,
        payload: AccountingPeriodUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> AccountingPeriod:
        period = await self.get(company_id, period_id)
        if payload.status is None:
            return period

        previous_status = period.status
        period.status = payload.status
        await self.db.flush()
        await self.db.refresh(period)

        action = AuditAction.ACCOUNTING_UPDATE
        if payload.status == PeriodStatus.CLOSED:
            action = AuditAction.PERIOD_CLOSED
        elif payload.status == PeriodStatus.LOCKED:
            action = AuditAction.PERIOD_LOCKED

        await self.audit.log(
            action=action,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="accounting_period",
            resource_id=str(period.id),
            description=f"Accounting period '{period.name}' status changed "
            f"{previous_status.value} -> {payload.status.value}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return period
