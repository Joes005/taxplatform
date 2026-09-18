import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.tds_enums import TDSQuarter
from app.models.tds_return_period import TDSReturnPeriod
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.tds_return_period_repository import TDSReturnPeriodRepository
from app.schemas.tds_return_period import TDSReturnPeriodCreate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

_QUARTER_OFFSET_MONTHS = {
    TDSQuarter.Q1: 0,
    TDSQuarter.Q2: 3,
    TDSQuarter.Q3: 6,
    TDSQuarter.Q4: 9,
}


def _add_months(on_date: date, months: int) -> date:
    total = on_date.month - 1 + months
    year = on_date.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def quarter_date_range(financial_year_start: date, quarter: TDSQuarter) -> tuple[date, date]:
    """Indian TDS quarters run Apr-Jun/Jul-Sep/Oct-Dec/Jan-Mar, i.e. three
    calendar months starting from the financial year's own start month —
    computed as an offset rather than hardcoded to April so a financial
    year starting on any month (Phase 3 allows configuring it) still gets
    correct quarter boundaries."""
    start = _add_months(financial_year_start, _QUARTER_OFFSET_MONTHS[quarter])
    next_quarter_start = _add_months(financial_year_start, _QUARTER_OFFSET_MONTHS[quarter] + 3)
    return start, next_quarter_start - timedelta(days=1)


class TDSReturnPeriodService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TDSReturnPeriodRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self,
        company_id: uuid.UUID,
        payload: TDSReturnPeriodCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> TDSReturnPeriod:
        financial_year = await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id)
        if financial_year is None:
            raise ValidationAppError(
                "Financial year not found for this company", code="INVALID_FINANCIAL_YEAR"
            )

        if await self.repo.get_by_quarter_for_company(company_id, financial_year.id, payload.quarter):
            raise ValidationAppError(
                f"A TDS return period already exists for {payload.quarter.value} of "
                f"'{financial_year.name}'",
                code="TDS_RETURN_PERIOD_ALREADY_EXISTS",
            )

        period_start, period_end = quarter_date_range(financial_year.start_date, payload.quarter)

        period = TDSReturnPeriod(
            company_id=company_id,
            financial_year_id=financial_year.id,
            quarter=payload.quarter,
            period_start=period_start,
            period_end=period_end,
        )
        await self.repo.create(period)

        await self.audit.log(
            action=AuditAction.TDS_RETURN_PERIOD_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_return_period",
            resource_id=str(period.id),
            description=f"TDS return period {payload.quarter.value} of '{financial_year.name}' created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return period

    async def get(self, company_id: uuid.UUID, period_id: uuid.UUID) -> TDSReturnPeriod:
        period = await self.repo.get_by_id_for_company(period_id, company_id)
        if period is None:
            raise NotFoundError("TDS return period not found", code="TDS_RETURN_PERIOD_NOT_FOUND")
        return period

    async def list(
        self, company_id: uuid.UUID, *, page: int, page_size: int
    ) -> tuple[list[TDSReturnPeriod], int]:
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size
        )
