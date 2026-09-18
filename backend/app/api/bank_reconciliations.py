import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.bank_reconciliation import (
    BankReconciliationActionRequest,
    BankReconciliationCreate,
    BankReconciliationRead,
    BankReconciliationSummary,
)
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.services.auth_service import RequestMeta
from app.services.bank_reconciliation_service import BankReconciliationService

router = APIRouter(prefix="/bank/reconciliations", tags=["bank-reconciliations"])


@router.post("", response_model=SuccessResponse[BankReconciliationRead], status_code=201)
async def start_reconciliation(
    company_id: uuid.UUID,
    payload: BankReconciliationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_RUN.value)),
):
    service = BankReconciliationService(db)
    reconciliation = await service.start(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=BankReconciliationRead.model_validate(reconciliation), message="Reconciliation session started"
    )


@router.get("", response_model=SuccessResponse[PaginatedData[BankReconciliationRead]])
async def list_reconciliations(
    company_id: uuid.UUID,
    bank_account_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_VIEW.value)),
):
    service = BankReconciliationService(db)
    items, total = await service.list(
        company_id, bank_account_id=bank_account_id, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[BankReconciliationRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{reconciliation_id}", response_model=SuccessResponse[BankReconciliationRead])
async def get_reconciliation(
    reconciliation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_VIEW.value)),
):
    service = BankReconciliationService(db)
    reconciliation = await service.get(company_id, reconciliation_id)
    return SuccessResponse(data=BankReconciliationRead.model_validate(reconciliation))


@router.get("/{reconciliation_id}/summary", response_model=SuccessResponse[BankReconciliationSummary])
async def get_reconciliation_summary(
    reconciliation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_VIEW.value)),
):
    service = BankReconciliationService(db)
    summary = await service.summary(company_id, reconciliation_id)
    return SuccessResponse(data=summary)


@router.post("/{reconciliation_id}/run-matching", response_model=SuccessResponse[BankReconciliationRead])
async def run_matching(
    reconciliation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_RUN.value)),
):
    service = BankReconciliationService(db)
    reconciliation = await service.run_matching(company_id, reconciliation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankReconciliationRead.model_validate(reconciliation), message="Matching run complete")


@router.post("/{reconciliation_id}/submit", response_model=SuccessResponse[BankReconciliationRead])
async def submit_reconciliation(
    reconciliation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_SUBMIT.value)),
):
    service = BankReconciliationService(db)
    reconciliation = await service.submit(company_id, reconciliation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankReconciliationRead.model_validate(reconciliation), message="Submitted for review")


@router.post("/{reconciliation_id}/approve", response_model=SuccessResponse[BankReconciliationRead])
async def approve_reconciliation(
    reconciliation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: BankReconciliationActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_APPROVE.value)),
):
    service = BankReconciliationService(db)
    reconciliation = await service.approve(company_id, reconciliation_id, current_user, meta, payload.comment)
    await db.commit()
    return SuccessResponse(data=BankReconciliationRead.model_validate(reconciliation), message="Approved")


@router.post("/{reconciliation_id}/reject", response_model=SuccessResponse[BankReconciliationRead])
async def reject_reconciliation(
    reconciliation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: BankReconciliationActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_APPROVE.value)),
):
    service = BankReconciliationService(db)
    reconciliation = await service.reject(company_id, reconciliation_id, current_user, meta, payload.comment)
    await db.commit()
    return SuccessResponse(
        data=BankReconciliationRead.model_validate(reconciliation), message="Returned for correction"
    )


@router.post("/{reconciliation_id}/lock", response_model=SuccessResponse[BankReconciliationRead])
async def lock_reconciliation(
    reconciliation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_LOCK.value)),
):
    service = BankReconciliationService(db)
    reconciliation = await service.lock(company_id, reconciliation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankReconciliationRead.model_validate(reconciliation), message="Locked")


@router.post("/{reconciliation_id}/cancel", response_model=SuccessResponse[BankReconciliationRead])
async def cancel_reconciliation(
    reconciliation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_RECONCILE_RUN.value)),
):
    service = BankReconciliationService(db)
    reconciliation = await service.cancel(company_id, reconciliation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankReconciliationRead.model_validate(reconciliation), message="Cancelled")
