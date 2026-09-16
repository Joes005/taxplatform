import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.gst_enums import ITCCategory, ReconciliationStatus
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.gst_reconciliation import GSTReconciliationRead, GSTReconciliationResultRead
from app.services.auth_service import RequestMeta
from app.services.gst_reconciliation_service import GSTReconciliationService

router = APIRouter(
    prefix="/gst/return-periods/{period_id}/reconciliation", tags=["gst-reconciliation"]
)


@router.post("", response_model=SuccessResponse[GSTReconciliationRead], status_code=201)
async def run_reconciliation(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GSTR2B_RECONCILE.value)),
):
    service = GSTReconciliationService(db)
    run = await service.run(company_id, period_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=GSTReconciliationRead.model_validate(run), message="Reconciliation complete")


@router.get("", response_model=SuccessResponse[GSTReconciliationRead])
async def get_latest_reconciliation(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR2B_VIEW.value)),
):
    service = GSTReconciliationService(db)
    run = await service.get_latest(company_id, period_id)
    return SuccessResponse(data=GSTReconciliationRead.model_validate(run))


@router.get("/results", response_model=SuccessResponse[PaginatedData[GSTReconciliationResultRead]])
async def list_reconciliation_results(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    status: ReconciliationStatus | None = Query(default=None),
    itc_category: ITCCategory | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR2B_VIEW.value)),
):
    service = GSTReconciliationService(db)
    items, total = await service.list_results(
        company_id, period_id, status=status, itc_category=itc_category, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[GSTReconciliationResultRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)
