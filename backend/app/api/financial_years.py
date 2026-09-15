import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.financial_year import FinancialYearCreate, FinancialYearRead, FinancialYearUpdate
from app.services.auth_service import RequestMeta
from app.services.financial_year_service import FinancialYearService

router = APIRouter(prefix="/accounting/financial-years", tags=["accounting-financial-years"])


@router.post("", response_model=SuccessResponse[FinancialYearRead], status_code=201)
async def create_financial_year(
    company_id: uuid.UUID,
    payload: FinancialYearCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_CREATE.value)),
):
    service = FinancialYearService(db)
    fy = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=FinancialYearRead.model_validate(fy), message="Financial year created")


@router.get("", response_model=SuccessResponse[PaginatedData[FinancialYearRead]])
async def list_financial_years(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = FinancialYearService(db)
    items, total = await service.list(company_id, page=page, page_size=page_size)
    data = PaginatedData(
        items=[FinancialYearRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{financial_year_id}", response_model=SuccessResponse[FinancialYearRead])
async def get_financial_year(
    financial_year_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = FinancialYearService(db)
    fy = await service.get(company_id, financial_year_id)
    return SuccessResponse(data=FinancialYearRead.model_validate(fy))


@router.patch("/{financial_year_id}", response_model=SuccessResponse[FinancialYearRead])
async def update_financial_year(
    financial_year_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: FinancialYearUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_UPDATE.value)),
):
    service = FinancialYearService(db)
    fy = await service.update(company_id, financial_year_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=FinancialYearRead.model_validate(fy), message="Financial year updated")
