import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.accounting_enums import TransactionStatus
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.purchase_invoice import (
    PurchaseInvoiceCreate,
    PurchaseInvoiceRead,
    PurchaseInvoiceUpdate,
)
from app.services.auth_service import RequestMeta
from app.services.purchase_invoice_service import PurchaseInvoiceService

router = APIRouter(prefix="/accounting/purchase-invoices", tags=["accounting-purchase-invoices"])


@router.post("", response_model=SuccessResponse[PurchaseInvoiceRead], status_code=201)
async def create_purchase_invoice(
    company_id: uuid.UUID,
    payload: PurchaseInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.PURCHASE_CREATE.value)),
):
    service = PurchaseInvoiceService(db)
    invoice = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=PurchaseInvoiceRead.model_validate(invoice), message="Purchase invoice created"
    )


@router.get("", response_model=SuccessResponse[PaginatedData[PurchaseInvoiceRead]])
async def list_purchase_invoices(
    company_id: uuid.UUID,
    status: TransactionStatus | None = Query(default=None),
    vendor_id: uuid.UUID | None = Query(default=None),
    financial_year_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.PURCHASE_VIEW.value)),
):
    service = PurchaseInvoiceService(db)
    items, total = await service.list(
        company_id,
        page=page,
        page_size=page_size,
        status=status,
        vendor_id=vendor_id,
        financial_year_id=financial_year_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    data = PaginatedData(
        items=[PurchaseInvoiceRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{invoice_id}", response_model=SuccessResponse[PurchaseInvoiceRead])
async def get_purchase_invoice(
    invoice_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.PURCHASE_VIEW.value)),
):
    service = PurchaseInvoiceService(db)
    invoice = await service.get(company_id, invoice_id)
    return SuccessResponse(data=PurchaseInvoiceRead.model_validate(invoice))


@router.patch("/{invoice_id}", response_model=SuccessResponse[PurchaseInvoiceRead])
async def update_purchase_invoice(
    invoice_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: PurchaseInvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.PURCHASE_UPDATE.value)),
):
    service = PurchaseInvoiceService(db)
    invoice = await service.update(company_id, invoice_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=PurchaseInvoiceRead.model_validate(invoice), message="Purchase invoice updated"
    )


@router.post("/{invoice_id}/post", response_model=SuccessResponse[PurchaseInvoiceRead])
async def post_purchase_invoice(
    invoice_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.PURCHASE_POST.value)),
):
    service = PurchaseInvoiceService(db)
    invoice = await service.post(company_id, invoice_id, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=PurchaseInvoiceRead.model_validate(invoice), message="Purchase invoice posted"
    )


@router.post("/{invoice_id}/cancel", response_model=SuccessResponse[PurchaseInvoiceRead])
async def cancel_purchase_invoice(
    invoice_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.PURCHASE_CANCEL.value)),
):
    service = PurchaseInvoiceService(db)
    invoice = await service.cancel(company_id, invoice_id, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=PurchaseInvoiceRead.model_validate(invoice), message="Purchase invoice cancelled"
    )
