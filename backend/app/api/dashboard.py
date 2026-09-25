import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.permissions import PermissionCode
from app.models.membership import CompanyMembership
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.dashboard import (
    CompanyHealth,
    DashboardActionItem,
    DashboardSummary,
    SetupProgress,
    WorkflowStage,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=SuccessResponse[DashboardSummary])
async def get_dashboard_summary(
    company_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(
        require_permission(PermissionCode.DASHBOARD_VIEW.value)
    ),
):
    role_code = (
        "SUPER_ADMIN"
        if current_user.is_platform_super_admin
        else (membership.role.code if membership and membership.role else "COMPANY_ADMIN")
    )
    service = DashboardService(db)
    summary = await service.get_summary(company_id, current_user, role_code)
    return SuccessResponse(data=summary)


@router.get("/actions", response_model=SuccessResponse[list[DashboardActionItem]])
async def get_dashboard_actions(
    company_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(
        require_permission(PermissionCode.DASHBOARD_VIEW.value)
    ),
):
    role_code = (
        "SUPER_ADMIN"
        if current_user.is_platform_super_admin
        else (membership.role.code if membership and membership.role else "COMPANY_ADMIN")
    )
    service = DashboardService(db)
    actions = await service.get_actions(company_id, current_user, role_code)
    return SuccessResponse(data=actions)


@router.get("/workflow", response_model=SuccessResponse[list[WorkflowStage]])
async def get_dashboard_workflow(
    company_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership: CompanyMembership | None = Depends(
        require_permission(PermissionCode.DASHBOARD_VIEW.value)
    ),
):
    service = DashboardService(db)
    stages = await service.get_workflow(company_id)
    return SuccessResponse(data=stages)


@router.get("/setup-progress", response_model=SuccessResponse[SetupProgress])
async def get_setup_progress(
    company_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership: CompanyMembership | None = Depends(
        require_permission(PermissionCode.DASHBOARD_VIEW.value)
    ),
):
    service = DashboardService(db)
    progress = await service.get_setup_progress(company_id)
    return SuccessResponse(data=progress)


@router.get("/health", response_model=SuccessResponse[CompanyHealth])
async def get_company_health(
    company_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership: CompanyMembership | None = Depends(
        require_permission(PermissionCode.DASHBOARD_VIEW.value)
    ),
):
    service = DashboardService(db)
    health = await service.get_health(company_id)
    return SuccessResponse(data=health)
