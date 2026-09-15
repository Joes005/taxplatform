import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.services.auth_service import RequestMeta
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/accounting/customers", tags=["accounting-customers"])


@router.post("", response_model=SuccessResponse[CustomerRead], status_code=201)
async def create_customer(
    company_id: uuid.UUID,
    payload: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.CUSTOMER_MANAGE.value)),
):
    service = CustomerService(db)
    customer = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=CustomerRead.model_validate(customer), message="Customer created")


@router.get("", response_model=SuccessResponse[PaginatedData[CustomerRead]])
async def list_customers(
    company_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.CUSTOMER_VIEW.value)),
):
    service = CustomerService(db)
    items, total = await service.list(
        company_id, search=search, is_active=is_active, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[CustomerRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{customer_id}", response_model=SuccessResponse[CustomerRead])
async def get_customer(
    customer_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.CUSTOMER_VIEW.value)),
):
    service = CustomerService(db)
    customer = await service.get(company_id, customer_id)
    return SuccessResponse(data=CustomerRead.model_validate(customer))


@router.patch("/{customer_id}", response_model=SuccessResponse[CustomerRead])
async def update_customer(
    customer_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.CUSTOMER_MANAGE.value)),
):
    service = CustomerService(db)
    customer = await service.update(company_id, customer_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=CustomerRead.model_validate(customer), message="Customer updated")
