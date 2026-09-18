import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.tds_enums import TDSTransactionStatus
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.tds_transaction import (
    TDSTransactionCreate,
    TDSTransactionOverride,
    TDSTransactionRead,
    TDSTransactionUpdate,
)
from app.services.auth_service import RequestMeta
from app.services.tds_transaction_service import TDSTransactionService

router = APIRouter(prefix="/tds/transactions", tags=["tds-transactions"])


@router.post("", response_model=SuccessResponse[TDSTransactionRead], status_code=201)
async def create_tds_transaction(
    company_id: uuid.UUID,
    payload: TDSTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_TRANSACTION_CREATE.value)),
):
    service = TDSTransactionService(db)
    transaction = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=TDSTransactionRead.model_validate(transaction), message="TDS transaction created"
    )


@router.get("", response_model=SuccessResponse[PaginatedData[TDSTransactionRead]])
async def list_tds_transactions(
    company_id: uuid.UUID,
    deductee_id: uuid.UUID | None = Query(default=None),
    tds_section_id: uuid.UUID | None = Query(default=None),
    status: TDSTransactionStatus | None = Query(default=None),
    financial_year_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_TRANSACTION_VIEW.value)),
):
    service = TDSTransactionService(db)
    items, total = await service.list(
        company_id,
        deductee_id=deductee_id,
        tds_section_id=tds_section_id,
        status=status,
        financial_year_id=financial_year_id,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[TDSTransactionRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/payable-summary", response_model=SuccessResponse[dict])
async def get_payable_summary(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_TRANSACTION_VIEW.value)),
):
    service = TDSTransactionService(db)
    summary = await service.payable_summary(company_id, financial_year_id=financial_year_id)
    return SuccessResponse(data={k: str(v) for k, v in summary.items()})


@router.get("/{transaction_id}", response_model=SuccessResponse[TDSTransactionRead])
async def get_tds_transaction(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_TRANSACTION_VIEW.value)),
):
    service = TDSTransactionService(db)
    transaction = await service.get(company_id, transaction_id)
    return SuccessResponse(data=TDSTransactionRead.model_validate(transaction))


@router.patch("/{transaction_id}", response_model=SuccessResponse[TDSTransactionRead])
async def update_tds_transaction(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSTransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_TRANSACTION_UPDATE.value)),
):
    service = TDSTransactionService(db)
    transaction = await service.update(company_id, transaction_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=TDSTransactionRead.model_validate(transaction), message="TDS transaction updated"
    )


@router.post("/{transaction_id}/calculate", response_model=SuccessResponse[TDSTransactionRead])
async def calculate_tds_transaction(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_TRANSACTION_CALCULATE.value)),
):
    service = TDSTransactionService(db)
    transaction = await service.calculate(company_id, transaction_id, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=TDSTransactionRead.model_validate(transaction), message="TDS transaction calculated"
    )


@router.post("/{transaction_id}/override", response_model=SuccessResponse[TDSTransactionRead])
async def override_tds_transaction(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSTransactionOverride,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_TRANSACTION_UPDATE.value)),
):
    service = TDSTransactionService(db)
    transaction = await service.override(company_id, transaction_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=TDSTransactionRead.model_validate(transaction), message="TDS transaction manually overridden"
    )


@router.post("/{transaction_id}/deduct", response_model=SuccessResponse[TDSTransactionRead])
async def deduct_tds_transaction(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    deduction_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_TRANSACTION_UPDATE.value)),
):
    service = TDSTransactionService(db)
    transaction = await service.deduct(
        company_id, transaction_id, current_user, meta, deduction_date=deduction_date
    )
    await db.commit()
    return SuccessResponse(
        data=TDSTransactionRead.model_validate(transaction), message="TDS transaction deducted"
    )


@router.post("/{transaction_id}/cancel", response_model=SuccessResponse[TDSTransactionRead])
async def cancel_tds_transaction(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_TRANSACTION_CANCEL.value)),
):
    service = TDSTransactionService(db)
    transaction = await service.cancel(company_id, transaction_id, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=TDSTransactionRead.model_validate(transaction), message="TDS transaction cancelled"
    )
