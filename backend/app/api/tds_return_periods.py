import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.tds_return_period import TDSReturnPeriodCreate, TDSReturnPeriodRead
from app.services.auth_service import RequestMeta
from app.services.tds_return_period_service import TDSReturnPeriodService

router = APIRouter(prefix="/tds/return-periods", tags=["tds-return-periods"])


@router.post("", response_model=SuccessResponse[TDSReturnPeriodRead], status_code=201)
async def create_return_period(
    company_id: uuid.UUID,
    payload: TDSReturnPeriodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_CREATE.value)),
):
    service = TDSReturnPeriodService(db)
    period = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=TDSReturnPeriodRead.model_validate(period), message="TDS return period created"
    )


@router.get("", response_model=SuccessResponse[PaginatedData[TDSReturnPeriodRead]])
async def list_return_periods(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_VIEW.value)),
):
    service = TDSReturnPeriodService(db)
    items, total = await service.list(company_id, page=page, page_size=page_size)
    data = PaginatedData(
        items=[TDSReturnPeriodRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{period_id}", response_model=SuccessResponse[TDSReturnPeriodRead])
async def get_return_period(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_VIEW.value)),
):
    service = TDSReturnPeriodService(db)
    period = await service.get(company_id, period_id)
    return SuccessResponse(data=TDSReturnPeriodRead.model_validate(period))
