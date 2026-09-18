import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.tds_enums import TDSReconciliationStatus
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.tds_reconciliation import TDSPaymentReconciliationRead
from app.services.auth_service import RequestMeta
from app.services.tds_reconciliation_service import TDSReconciliationService

router = APIRouter(prefix="/tds/reconciliation", tags=["tds-reconciliation"])


@router.post("/run", response_model=SuccessResponse[list[TDSPaymentReconciliationRead]])
async def run_tds_reconciliation(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_CHALLAN_RECONCILE.value)),
):
    service = TDSReconciliationService(db)
    rows = await service.run(company_id, financial_year_id, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=[TDSPaymentReconciliationRead.model_validate(r) for r in rows],
        message=f"Reconciliation complete: {len(rows)} findings",
    )


@router.get("", response_model=SuccessResponse[PaginatedData[TDSPaymentReconciliationRead]])
async def list_tds_reconciliation(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID | None = Query(default=None),
    status: TDSReconciliationStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_CHALLAN_VIEW.value)),
):
    service = TDSReconciliationService(db)
    items, total = await service.list(
        company_id, financial_year_id=financial_year_id, status=status, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[TDSPaymentReconciliationRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)
