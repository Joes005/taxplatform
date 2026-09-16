import calendar
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.gst_return_period import GSTReturnPeriod
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.gst_return_period_repository import GSTReturnPeriodRepository
from app.schemas.gst_return_period import GSTReturnPeriodCreate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class GSTReturnPeriodService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GSTReturnPeriodRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self,
        company_id: uuid.UUID,
        payload: GSTReturnPeriodCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> GSTReturnPeriod:
        financial_year = await self.fy_repo.get_by_id_for_company(
            payload.financial_year_id, company_id
        )
        if financial_year is None:
            raise ValidationAppError(
                "Financial year not found for this company", code="INVALID_FINANCIAL_YEAR"
            )

        if await self.repo.get_by_year_month_for_company(company_id, payload.year, payload.month):
            raise ValidationAppError(
                f"A return period already exists for {payload.month}/{payload.year}",
                code="GST_RETURN_PERIOD_ALREADY_EXISTS",
            )

        last_day = calendar.monthrange(payload.year, payload.month)[1]
        period_start = date(payload.year, payload.month, 1)
        period_end = date(payload.year, payload.month, last_day)

        if not (financial_year.start_date <= period_start and period_end <= financial_year.end_date):
            raise ValidationAppError(
                f"{payload.month}/{payload.year} falls outside financial year '{financial_year.name}'",
                code="PERIOD_OUTSIDE_FINANCIAL_YEAR",
            )

        period = GSTReturnPeriod(
            company_id=company_id,
            financial_year_id=financial_year.id,
            year=payload.year,
            month=payload.month,
            period_start=period_start,
            period_end=period_end,
        )
        await self.repo.create(period)

        await self.audit.log(
            action=AuditAction.GST_RETURN_PERIOD_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="gst_return_period",
            resource_id=str(period.id),
            description=f"GST return period {payload.month}/{payload.year} created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return period

    async def get(self, company_id: uuid.UUID, period_id: uuid.UUID) -> GSTReturnPeriod:
        period = await self.repo.get_by_id_for_company(period_id, company_id)
        if period is None:
            raise NotFoundError("GST return period not found", code="GST_RETURN_PERIOD_NOT_FOUND")
        return period

    async def list(
        self, company_id: uuid.UUID, *, page: int, page_size: int
    ) -> tuple[list[GSTReturnPeriod], int]:
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size
        )
