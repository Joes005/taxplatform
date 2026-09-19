import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.compliance_calendar import CalendarDay, ComplianceDashboard
from app.services.compliance_calendar_service import ComplianceCalendarService

router = APIRouter(prefix="/compliance", tags=["compliance-calendar"])


@router.get("/calendar", response_model=SuccessResponse[list[CalendarDay]])
async def get_calendar_range(
    company_id: uuid.UUID,
    start: date = Query(...),
    end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_CALENDAR_VIEW.value)),
):
    service = ComplianceCalendarService(db)
    days = await service.calendar_range(company_id, start=start, end=end)
    return SuccessResponse(data=days)


@router.get("/calendar/month", response_model=SuccessResponse[list[CalendarDay]])
async def get_calendar_month(
    company_id: uuid.UUID,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_CALENDAR_VIEW.value)),
):
    service = ComplianceCalendarService(db)
    days = await service.calendar_month(company_id, year=year, month=month)
    return SuccessResponse(data=days)


@router.get("/calendar/week", response_model=SuccessResponse[list[CalendarDay]])
async def get_calendar_week(
    company_id: uuid.UUID,
    start: date = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_CALENDAR_VIEW.value)),
):
    service = ComplianceCalendarService(db)
    days = await service.calendar_week(company_id, start=start)
    return SuccessResponse(data=days)


@router.get("/dashboard", response_model=SuccessResponse[ComplianceDashboard])
async def get_dashboard(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceCalendarService(db)
    dashboard = await service.dashboard(company_id, current_user)
    await db.commit()
    return SuccessResponse(data=dashboard)
