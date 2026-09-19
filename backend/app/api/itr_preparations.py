import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.itr_preparation import ITRPreparationRead, ITRValidationResult
from app.services.auth_service import RequestMeta
from app.services.itr_preparation_service import ITRPreparationService

router = APIRouter(prefix="/income-tax/itr", tags=["itr-preparations"])


class ITRPreparationCreateRequest(BaseModel):
    tax_computation_id: uuid.UUID


@router.post("", response_model=SuccessResponse[ITRPreparationRead], status_code=201)
async def create_preparation(
    company_id: uuid.UUID,
    payload: ITRPreparationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = ITRPreparationService(db)
    preparation = await service.create(company_id, payload.tax_computation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ITRPreparationRead.model_validate(preparation), message="ITR preparation created")


@router.get("", response_model=SuccessResponse[PaginatedData[ITRPreparationRead]])
async def list_preparations(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = ITRPreparationService(db)
    items, total = await service.list_for_company(company_id, page=page, page_size=page_size)
    data = PaginatedData(
        items=[ITRPreparationRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{preparation_id}", response_model=SuccessResponse[ITRPreparationRead])
async def get_preparation(
    preparation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = ITRPreparationService(db)
    preparation = await service.get(company_id, preparation_id)
    return SuccessResponse(data=ITRPreparationRead.model_validate(preparation))


@router.post("/{preparation_id}/validate", response_model=SuccessResponse[ITRValidationResult])
async def validate_preparation(
    preparation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VALIDATE.value)),
):
    service = ITRPreparationService(db)
    preparation, issues = await service.validate(company_id, preparation_id, current_user, meta)
    await db.commit()
    has_errors = any(issue.severity == "ERROR" for issue in issues)
    result = ITRValidationResult(
        preparation=ITRPreparationRead.model_validate(preparation), issues=issues, has_errors=has_errors
    )
    return SuccessResponse(data=result, message="Validation complete")


@router.post("/{preparation_id}/submit-review", response_model=SuccessResponse[ITRPreparationRead])
async def submit_preparation_for_review(
    preparation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_REVIEW.value)),
):
    service = ITRPreparationService(db)
    preparation = await service.submit_for_review(company_id, preparation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ITRPreparationRead.model_validate(preparation), message="Submitted for review")


@router.post("/{preparation_id}/approve", response_model=SuccessResponse[ITRPreparationRead])
async def approve_preparation(
    preparation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_APPROVE.value)),
):
    service = ITRPreparationService(db)
    preparation = await service.approve(company_id, preparation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ITRPreparationRead.model_validate(preparation), message="ITR preparation approved")


@router.post("/{preparation_id}/lock", response_model=SuccessResponse[ITRPreparationRead])
async def lock_preparation(
    preparation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_LOCK.value)),
):
    service = ITRPreparationService(db)
    preparation = await service.lock(company_id, preparation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ITRPreparationRead.model_validate(preparation), message="ITR preparation locked")
