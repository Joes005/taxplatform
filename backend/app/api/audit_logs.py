import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import PermissionDeniedError, ValidationAppError
from app.core.permissions import PermissionCode
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.audit_log import AuditLogRead
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=SuccessResponse[PaginatedData[AuditLogRead]])
async def list_audit_logs(
    company_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_platform_super_admin:
        if company_id is None:
            raise ValidationAppError(
                "company_id is required to view audit logs for a specific company"
            )
        membership = await MembershipRepository(db).get_active_membership(
            user_id=current_user.id, company_id=company_id
        )
        if membership is None:
            raise PermissionDeniedError("You do not have access to this company's audit logs")
        codes = await RoleRepository(db).get_permission_codes_for_role(membership.role_id)
        if PermissionCode.AUDIT_LOG_VIEW.value not in codes:
            raise PermissionDeniedError("You do not have permission to view audit logs")

    offset = (page - 1) * page_size
    items, total = await AuditRepository(db).list_filtered(
        company_id=company_id,
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=page_size,
    )

    data = PaginatedData(
        items=[AuditLogRead.model_validate(item) for item in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)
