import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.deductee import DeducteeCreate, DeducteeRead, DeducteeUpdate
from app.services.auth_service import RequestMeta
from app.services.deductee_service import DeducteeService

router = APIRouter(prefix="/tds/deductees", tags=["tds-deductees"])


@router.post("", response_model=SuccessResponse[DeducteeRead], status_code=201)
async def create_deductee(
    company_id: uuid.UUID,
    payload: DeducteeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_DEDUCTEE_MANAGE.value)),
):
    service = DeducteeService(db)
    deductee = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=DeducteeRead.model_validate(deductee), message="Deductee created")


@router.get("", response_model=SuccessResponse[PaginatedData[DeducteeRead]])
async def list_deductees(
    company_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_DEDUCTEE_VIEW.value)),
):
    service = DeducteeService(db)
    items, total = await service.list(
        company_id, search=search, is_active=is_active, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[DeducteeRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{deductee_id}", response_model=SuccessResponse[DeducteeRead])
async def get_deductee(
    deductee_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_DEDUCTEE_VIEW.value)),
):
    service = DeducteeService(db)
    deductee = await service.get(company_id, deductee_id)
    return SuccessResponse(data=DeducteeRead.model_validate(deductee))


@router.patch("/{deductee_id}", response_model=SuccessResponse[DeducteeRead])
async def update_deductee(
    deductee_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: DeducteeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_DEDUCTEE_MANAGE.value)),
):
    service = DeducteeService(db)
    deductee = await service.update(company_id, deductee_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=DeducteeRead.model_validate(deductee), message="Deductee updated")
