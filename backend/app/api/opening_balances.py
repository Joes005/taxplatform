import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.accounting_enums import OpeningBalanceAccountType
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.opening_balance import OpeningBalanceCreate, OpeningBalanceRead
from app.services.auth_service import RequestMeta
from app.services.opening_balance_service import OpeningBalanceService

router = APIRouter(prefix="/accounting/opening-balances", tags=["accounting-opening-balances"])


@router.post("", response_model=SuccessResponse[OpeningBalanceRead], status_code=201)
async def create_opening_balance(
    company_id: uuid.UUID,
    payload: OpeningBalanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_CREATE.value)),
):
    service = OpeningBalanceService(db)
    ob = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=OpeningBalanceRead.model_validate(ob), message="Opening balance created")


@router.get("", response_model=SuccessResponse[PaginatedData[OpeningBalanceRead]])
async def list_opening_balances(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID | None = Query(default=None),
    account_type: OpeningBalanceAccountType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = OpeningBalanceService(db)
    items, total = await service.list(
        company_id,
        page=page,
        page_size=page_size,
        financial_year_id=financial_year_id,
        account_type=account_type,
    )
    data = PaginatedData(
        items=[OpeningBalanceRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)
