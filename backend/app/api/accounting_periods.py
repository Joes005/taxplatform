import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.accounting_period import (
    AccountingPeriodCreate,
    AccountingPeriodRead,
    AccountingPeriodUpdate,
)
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.services.accounting_period_service import AccountingPeriodService
from app.services.auth_service import RequestMeta

router = APIRouter(prefix="/accounting/periods", tags=["accounting-periods"])


@router.post("", response_model=SuccessResponse[AccountingPeriodRead], status_code=201)
async def create_period(
    company_id: uuid.UUID,
    payload: AccountingPeriodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_CREATE.value)),
):
    service = AccountingPeriodService(db)
    period = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=AccountingPeriodRead.model_validate(period), message="Accounting period created"
    )


@router.get("", response_model=SuccessResponse[PaginatedData[AccountingPeriodRead]])
async def list_periods(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = AccountingPeriodService(db)
    items, total = await service.list(
        company_id, financial_year_id=financial_year_id, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[AccountingPeriodRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.patch("/{period_id}", response_model=SuccessResponse[AccountingPeriodRead])
async def update_period(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AccountingPeriodUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_UPDATE.value)),
):
    service = AccountingPeriodService(db)
    period = await service.update_status(company_id, period_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=AccountingPeriodRead.model_validate(period), message="Accounting period updated"
    )
