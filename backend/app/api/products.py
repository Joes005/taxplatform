import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.product_service import ProductServiceCreate, ProductServiceRead, ProductServiceUpdate
from app.services.auth_service import RequestMeta
from app.services.product_catalog_service import ProductCatalogService

router = APIRouter(prefix="/accounting/products", tags=["accounting-products"])


@router.post("", response_model=SuccessResponse[ProductServiceRead], status_code=201)
async def create_product(
    company_id: uuid.UUID,
    payload: ProductServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.PRODUCT_MANAGE.value)),
):
    service = ProductCatalogService(db)
    product = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ProductServiceRead.model_validate(product), message="Product created")


@router.get("", response_model=SuccessResponse[PaginatedData[ProductServiceRead]])
async def list_products(
    company_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.PRODUCT_VIEW.value)),
):
    service = ProductCatalogService(db)
    items, total = await service.list(
        company_id, search=search, is_active=is_active, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[ProductServiceRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{product_id}", response_model=SuccessResponse[ProductServiceRead])
async def get_product(
    product_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.PRODUCT_VIEW.value)),
):
    service = ProductCatalogService(db)
    product = await service.get(company_id, product_id)
    return SuccessResponse(data=ProductServiceRead.model_validate(product))


@router.patch("/{product_id}", response_model=SuccessResponse[ProductServiceRead])
async def update_product(
    product_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ProductServiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.PRODUCT_MANAGE.value)),
):
    service = ProductCatalogService(db)
    product = await service.update(company_id, product_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ProductServiceRead.model_validate(product), message="Product updated")
