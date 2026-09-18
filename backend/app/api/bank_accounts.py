import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.bank_account import BankAccountCreate, BankAccountRead, BankAccountUpdate
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.services.auth_service import RequestMeta
from app.services.bank_account_service import BankAccountService

router = APIRouter(prefix="/bank/accounts", tags=["bank-accounts"])


@router.post("", response_model=SuccessResponse[BankAccountRead], status_code=201)
async def create_bank_account(
    company_id: uuid.UUID,
    payload: BankAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_CREATE.value)),
):
    service = BankAccountService(db)
    account = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankAccountRead.model_validate(account), message="Bank account created")


@router.get("", response_model=SuccessResponse[PaginatedData[BankAccountRead]])
async def list_bank_accounts(
    company_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_VIEW.value)),
):
    service = BankAccountService(db)
    items, total = await service.list(
        company_id, search=search, is_active=is_active, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[BankAccountRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{account_id}", response_model=SuccessResponse[BankAccountRead])
async def get_bank_account(
    account_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_VIEW.value)),
):
    service = BankAccountService(db)
    account = await service.get(company_id, account_id)
    return SuccessResponse(data=BankAccountRead.model_validate(account))


@router.patch("/{account_id}", response_model=SuccessResponse[BankAccountRead])
async def update_bank_account(
    account_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: BankAccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_UPDATE.value)),
):
    service = BankAccountService(db)
    account = await service.update(company_id, account_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankAccountRead.model_validate(account), message="Bank account updated")
