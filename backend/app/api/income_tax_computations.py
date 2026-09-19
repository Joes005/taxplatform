import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.tax_computation import TaxComputationCreate, TaxComputationRead, TaxComputationSnapshotRead
from app.services.auth_service import RequestMeta
from app.services.income_tax_computation_service import IncomeTaxComputationService

router = APIRouter(prefix="/income-tax/computations", tags=["income-tax-computations"])


@router.post("", response_model=SuccessResponse[TaxComputationRead], status_code=201)
async def create_computation(
    company_id: uuid.UUID,
    payload: TaxComputationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxComputationService(db)
    computation = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TaxComputationRead.model_validate(computation), message="Tax computation created")


@router.get("", response_model=SuccessResponse[PaginatedData[TaxComputationRead]])
async def list_computations(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxComputationService(db)
    items, total = await service.list_for_company(company_id, page=page, page_size=page_size)
    data = PaginatedData(
        items=[TaxComputationRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{computation_id}", response_model=SuccessResponse[TaxComputationRead])
async def get_computation(
    computation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxComputationService(db)
    computation = await service.get(company_id, computation_id)
    return SuccessResponse(data=TaxComputationRead.model_validate(computation))


@router.get("/{computation_id}/snapshots", response_model=SuccessResponse[list[TaxComputationSnapshotRead]])
async def list_snapshots(
    computation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxComputationService(db)
    await service.get(company_id, computation_id)
    snapshots = await service.list_snapshots(computation_id)
    return SuccessResponse(data=[TaxComputationSnapshotRead.model_validate(s) for s in snapshots])


@router.post("/{computation_id}/calculate", response_model=SuccessResponse[TaxComputationRead])
async def calculate_computation(
    computation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CALCULATE.value)),
):
    service = IncomeTaxComputationService(db)
    computation = await service.calculate(company_id, computation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TaxComputationRead.model_validate(computation), message="Tax computation calculated")


@router.post("/{computation_id}/submit-review", response_model=SuccessResponse[TaxComputationRead])
async def submit_computation_for_review(
    computation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_REVIEW.value)),
):
    service = IncomeTaxComputationService(db)
    computation = await service.submit_for_review(company_id, computation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=TaxComputationRead.model_validate(computation), message="Submitted for auditor review"
    )


@router.post("/{computation_id}/approve", response_model=SuccessResponse[TaxComputationRead])
async def approve_computation(
    computation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_APPROVE.value)),
):
    service = IncomeTaxComputationService(db)
    computation = await service.approve(company_id, computation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TaxComputationRead.model_validate(computation), message="Tax computation approved")


@router.post("/{computation_id}/lock", response_model=SuccessResponse[TaxComputationRead])
async def lock_computation(
    computation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_LOCK.value)),
):
    service = IncomeTaxComputationService(db)
    computation = await service.lock(company_id, computation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TaxComputationRead.model_validate(computation), message="Tax computation locked")


@router.post("/{computation_id}/cancel", response_model=SuccessResponse[TaxComputationRead])
async def cancel_computation(
    computation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxComputationService(db)
    computation = await service.cancel(company_id, computation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TaxComputationRead.model_validate(computation), message="Tax computation cancelled")
