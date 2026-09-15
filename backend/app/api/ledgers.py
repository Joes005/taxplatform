import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.ledger import LedgerCreate, LedgerRead, LedgerUpdate
from app.services.auth_service import RequestMeta
from app.services.ledger_service import LedgerService

router = APIRouter(prefix="/accounting/ledgers", tags=["accounting-ledgers"])


@router.post("", response_model=SuccessResponse[LedgerRead], status_code=201)
async def create_ledger(
    company_id: uuid.UUID,
    payload: LedgerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.LEDGER_MANAGE.value)),
):
    service = LedgerService(db)
    ledger = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=LedgerRead.model_validate(ledger), message="Ledger created")


@router.get("", response_model=SuccessResponse[PaginatedData[LedgerRead]])
async def list_ledgers(
    company_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.LEDGER_VIEW.value)),
):
    service = LedgerService(db)
    items, total = await service.list(
        company_id, search=search, is_active=is_active, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[LedgerRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{ledger_id}", response_model=SuccessResponse[LedgerRead])
async def get_ledger(
    ledger_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.LEDGER_VIEW.value)),
):
    service = LedgerService(db)
    ledger = await service.get(company_id, ledger_id)
    return SuccessResponse(data=LedgerRead.model_validate(ledger))


@router.patch("/{ledger_id}", response_model=SuccessResponse[LedgerRead])
async def update_ledger(
    ledger_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: LedgerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.LEDGER_MANAGE.value)),
):
    service = LedgerService(db)
    ledger = await service.update(company_id, ledger_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=LedgerRead.model_validate(ledger), message="Ledger updated")
