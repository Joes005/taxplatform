import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.receipt import ReceiptCreate, ReceiptRead
from app.services.auth_service import RequestMeta
from app.services.receipt_service import ReceiptService

router = APIRouter(prefix="/accounting/receipts", tags=["accounting-receipts"])


@router.post("", response_model=SuccessResponse[ReceiptRead], status_code=201)
async def create_receipt(
    company_id: uuid.UUID,
    payload: ReceiptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.RECEIPT_CREATE.value)),
):
    service = ReceiptService(db)
    receipt = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ReceiptRead.model_validate(receipt), message="Receipt recorded")


@router.get("", response_model=SuccessResponse[PaginatedData[ReceiptRead]])
async def list_receipts(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.RECEIPT_VIEW.value)),
):
    service = ReceiptService(db)
    items, total = await service.list(
        company_id,
        page=page,
        page_size=page_size,
        financial_year_id=financial_year_id,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
    )
    data = PaginatedData(
        items=[ReceiptRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{receipt_id}", response_model=SuccessResponse[ReceiptRead])
async def get_receipt(
    receipt_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.RECEIPT_VIEW.value)),
):
    service = ReceiptService(db)
    receipt = await service.get(company_id, receipt_id)
    return SuccessResponse(data=ReceiptRead.model_validate(receipt))
