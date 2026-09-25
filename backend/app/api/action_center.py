import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.permissions import PermissionCode
from app.models.membership import CompanyMembership
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.dashboard import ActionCenterItem
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/action-center", tags=["action-center"])


@router.get("", response_model=SuccessResponse[PaginatedData[ActionCenterItem]])
async def list_action_center_items(
    company_id: uuid.UUID = Query(...),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    module: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
    result = await service.get_action_center(
        company_id,
        current_user,
        role_code,
        category=category,
        severity=severity,
        module=module,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=result["items"],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=result["total"]),
    )
    return SuccessResponse(data=data)
