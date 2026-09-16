import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.gst_return_period import GSTReturnPeriodCreate, GSTReturnPeriodRead
from app.services.auth_service import RequestMeta
from app.services.gst_return_period_service import GSTReturnPeriodService

router = APIRouter(prefix="/gst/return-periods", tags=["gst-return-periods"])


@router.post("", response_model=SuccessResponse[GSTReturnPeriodRead], status_code=201)
async def create_return_period(
    company_id: uuid.UUID,
    payload: GSTReturnPeriodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_CREATE.value)),
):
    service = GSTReturnPeriodService(db)
    period = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=GSTReturnPeriodRead.model_validate(period), message="GST return period created"
    )


@router.get("", response_model=SuccessResponse[PaginatedData[GSTReturnPeriodRead]])
async def list_return_periods(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_VIEW.value)),
):
    service = GSTReturnPeriodService(db)
    items, total = await service.list(company_id, page=page, page_size=page_size)
    data = PaginatedData(
        items=[GSTReturnPeriodRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{period_id}", response_model=SuccessResponse[GSTReturnPeriodRead])
async def get_return_period(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_VIEW.value)),
):
    service = GSTReturnPeriodService(db)
    period = await service.get(company_id, period_id)
    return SuccessResponse(data=GSTReturnPeriodRead.model_validate(period))
