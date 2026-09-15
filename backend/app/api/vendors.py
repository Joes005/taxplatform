import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.vendor import VendorCreate, VendorRead, VendorUpdate
from app.services.auth_service import RequestMeta
from app.services.vendor_service import VendorService

router = APIRouter(prefix="/accounting/vendors", tags=["accounting-vendors"])


@router.post("", response_model=SuccessResponse[VendorRead], status_code=201)
async def create_vendor(
    company_id: uuid.UUID,
    payload: VendorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.VENDOR_MANAGE.value)),
):
    service = VendorService(db)
    vendor = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=VendorRead.model_validate(vendor), message="Vendor created")


@router.get("", response_model=SuccessResponse[PaginatedData[VendorRead]])
async def list_vendors(
    company_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.VENDOR_VIEW.value)),
):
    service = VendorService(db)
    items, total = await service.list(
        company_id, search=search, is_active=is_active, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[VendorRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{vendor_id}", response_model=SuccessResponse[VendorRead])
async def get_vendor(
    vendor_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.VENDOR_VIEW.value)),
):
    service = VendorService(db)
    vendor = await service.get(company_id, vendor_id)
    return SuccessResponse(data=VendorRead.model_validate(vendor))


@router.patch("/{vendor_id}", response_model=SuccessResponse[VendorRead])
async def update_vendor(
    vendor_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.VENDOR_MANAGE.value)),
):
    service = VendorService(db)
    vendor = await service.update(company_id, vendor_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=VendorRead.model_validate(vendor), message="Vendor updated")
