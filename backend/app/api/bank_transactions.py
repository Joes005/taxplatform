import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.bank_enums import BankTransactionReconciliationStatus
from app.models.user import User
from app.schemas.bank_adjustment import BankAdjustmentCreate
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.journal_entry import JournalEntryRead
from app.schemas.bank_transaction import BankTransactionRead
from app.services.auth_service import RequestMeta
from app.services.bank_adjustment_service import BankAdjustmentService
from app.services.bank_transaction_service import BankTransactionService

router = APIRouter(prefix="/bank/transactions", tags=["bank-transactions"])


@router.get("", response_model=SuccessResponse[PaginatedData[BankTransactionRead]])
async def list_bank_transactions(
    company_id: uuid.UUID,
    bank_account_id: uuid.UUID | None = Query(default=None),
    reconciliation_status: BankTransactionReconciliationStatus | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_TRANSACTION_VIEW.value)),
):
    service = BankTransactionService(db)
    items, total = await service.list(
        company_id,
        bank_account_id=bank_account_id,
        reconciliation_status=reconciliation_status,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[BankTransactionRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{transaction_id}", response_model=SuccessResponse[BankTransactionRead])
async def get_bank_transaction(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_TRANSACTION_VIEW.value)),
):
    service = BankTransactionService(db)
    transaction = await service.get(company_id, transaction_id)
    return SuccessResponse(data=BankTransactionRead.model_validate(transaction))


@router.post("/{transaction_id}/exclude", response_model=SuccessResponse[BankTransactionRead])
async def exclude_bank_transaction(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_TRANSACTION_UPDATE.value)),
):
    service = BankTransactionService(db)
    transaction = await service.exclude(company_id, transaction_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankTransactionRead.model_validate(transaction), message="Transaction excluded")


@router.post("/{transaction_id}/review", response_model=SuccessResponse[BankTransactionRead])
async def flag_bank_transaction_for_review(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_TRANSACTION_UPDATE.value)),
):
    service = BankTransactionService(db)
    transaction = await service.mark_review_required(company_id, transaction_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankTransactionRead.model_validate(transaction), message="Flagged for review")


@router.post("/{transaction_id}/adjust", response_model=SuccessResponse[JournalEntryRead], status_code=201)
async def create_bank_adjustment(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: BankAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_ADJUST.value)),
):
    service = BankAdjustmentService(db)
    entry = await service.create_adjustment(company_id, transaction_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=JournalEntryRead.model_validate(entry), message="Adjustment journal entry created and posted"
    )
