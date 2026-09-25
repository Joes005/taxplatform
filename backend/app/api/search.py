import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.permissions import PermissionCode
from app.models.membership import CompanyMembership
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.search import SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SuccessResponse[SearchResponse])
async def search_company_entities(
    company_id: uuid.UUID = Query(...),
    q: str = Query(default="", min_length=1, max_length=100),
    type: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
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
    service = SearchService(db)
    result = await service.search(
        company_id=company_id,
        query=q,
        current_user=current_user,
        role_code=role_code,
        type_filter=type,
        limit=limit,
    )
    return SuccessResponse(data=result)
