import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.bank_enums import BankTransactionReconciliationStatus
from app.models.user import User
from app.schemas.bank_statement import BankStatementBalanceCheck, BankStatementCreate, BankStatementRead
from app.schemas.bank_transaction import BankTransactionRead
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.services.auth_service import RequestMeta
from app.services.bank_statement_service import BankStatementService
from app.services.bank_transaction_service import BankTransactionService

router = APIRouter(prefix="/bank/statements", tags=["bank-statements"])


@router.post("", response_model=SuccessResponse[BankStatementRead], status_code=201)
async def create_bank_statement(
    company_id: uuid.UUID,
    payload: BankStatementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_STATEMENT_IMPORT.value)),
):
    service = BankStatementService(db)
    statement = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=BankStatementRead.model_validate(statement),
        message="Bank statement registered — import its transactions next",
    )


@router.get("", response_model=SuccessResponse[PaginatedData[BankStatementRead]])
async def list_bank_statements(
    company_id: uuid.UUID,
    bank_account_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_STATEMENT_VIEW.value)),
):
    service = BankStatementService(db)
    items, total = await service.list(
        company_id, bank_account_id=bank_account_id, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[BankStatementRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{statement_id}", response_model=SuccessResponse[BankStatementRead])
async def get_bank_statement(
    statement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_STATEMENT_VIEW.value)),
):
    service = BankStatementService(db)
    statement = await service.get(company_id, statement_id)
    return SuccessResponse(data=BankStatementRead.model_validate(statement))


@router.get("/{statement_id}/balance-check", response_model=SuccessResponse[BankStatementBalanceCheck])
async def check_bank_statement_balance(
    statement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_STATEMENT_VIEW.value)),
):
    service = BankStatementService(db)
    result = await service.validate_balance(company_id, statement_id)
    return SuccessResponse(data=result)


@router.get("/{statement_id}/transactions", response_model=SuccessResponse[PaginatedData[BankTransactionRead]])
async def list_bank_statement_transactions(
    statement_id: uuid.UUID,
    company_id: uuid.UUID,
    reconciliation_status: BankTransactionReconciliationStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_TRANSACTION_VIEW.value)),
):
    service = BankTransactionService(db)
    items, total = await service.list(
        company_id,
        bank_statement_id=statement_id,
        reconciliation_status=reconciliation_status,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[BankTransactionRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.post("/{statement_id}/archive", response_model=SuccessResponse[BankStatementRead])
async def archive_bank_statement(
    statement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_STATEMENT_IMPORT.value)),
):
    service = BankStatementService(db)
    statement = await service.archive(company_id, statement_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankStatementRead.model_validate(statement), message="Bank statement archived")
