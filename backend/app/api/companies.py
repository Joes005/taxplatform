import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    get_request_meta,
    require_permission,
    require_platform_super_admin,
)
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.auth_service import RequestMeta
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=SuccessResponse[CompanyRead], status_code=201)
async def create_company(
    payload: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_super_admin),
    meta: RequestMeta = Depends(get_request_meta),
):
    service = CompanyService(db)
    company = await service.create_company(payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=CompanyRead.model_validate(company), message="Company created")


@router.get("", response_model=SuccessResponse[PaginatedData[CompanyRead]])
async def list_companies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CompanyService(db)
    companies, total = await service.list_companies(current_user, page=page, page_size=page_size)
    data = PaginatedData(
        items=[CompanyRead.model_validate(c) for c in companies],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{company_id}", response_model=SuccessResponse[CompanyRead])
async def get_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPANY_VIEW.value)),
):
    service = CompanyService(db)
    company = await service.get_company(company_id)
    return SuccessResponse(data=CompanyRead.model_validate(company))


@router.patch("/{company_id}", response_model=SuccessResponse[CompanyRead])
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPANY_UPDATE.value)),
):
    service = CompanyService(db)
    company = await service.update_company(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=CompanyRead.model_validate(company), message="Company updated")
