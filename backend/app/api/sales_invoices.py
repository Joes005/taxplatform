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
from app.schemas.sales_invoice import SalesInvoiceCreate, SalesInvoiceRead, SalesInvoiceUpdate
from app.services.auth_service import RequestMeta
from app.services.sales_invoice_service import SalesInvoiceService

router = APIRouter(prefix="/accounting/sales-invoices", tags=["accounting-sales-invoices"])


@router.post("", response_model=SuccessResponse[SalesInvoiceRead], status_code=201)
async def create_sales_invoice(
    company_id: uuid.UUID,
    payload: SalesInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.SALES_CREATE.value)),
):
    service = SalesInvoiceService(db)
    invoice = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=SalesInvoiceRead.model_validate(invoice), message="Sales invoice created")


@router.get("", response_model=SuccessResponse[PaginatedData[SalesInvoiceRead]])
async def list_sales_invoices(
    company_id: uuid.UUID,
    status: TransactionStatus | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    financial_year_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.SALES_VIEW.value)),
):
    service = SalesInvoiceService(db)
    items, total = await service.list(
        company_id,
        page=page,
        page_size=page_size,
        status=status,
        customer_id=customer_id,
        financial_year_id=financial_year_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    data = PaginatedData(
        items=[SalesInvoiceRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{invoice_id}", response_model=SuccessResponse[SalesInvoiceRead])
async def get_sales_invoice(
    invoice_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.SALES_VIEW.value)),
):
    service = SalesInvoiceService(db)
    invoice = await service.get(company_id, invoice_id)
    return SuccessResponse(data=SalesInvoiceRead.model_validate(invoice))


@router.patch("/{invoice_id}", response_model=SuccessResponse[SalesInvoiceRead])
async def update_sales_invoice(
    invoice_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: SalesInvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.SALES_UPDATE.value)),
):
    service = SalesInvoiceService(db)
    invoice = await service.update(company_id, invoice_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=SalesInvoiceRead.model_validate(invoice), message="Sales invoice updated")


@router.post("/{invoice_id}/post", response_model=SuccessResponse[SalesInvoiceRead])
async def post_sales_invoice(
    invoice_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.SALES_POST.value)),
):
    service = SalesInvoiceService(db)
    invoice = await service.post(company_id, invoice_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=SalesInvoiceRead.model_validate(invoice), message="Sales invoice posted")


@router.post("/{invoice_id}/cancel", response_model=SuccessResponse[SalesInvoiceRead])
async def cancel_sales_invoice(
    invoice_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.SALES_CANCEL.value)),
):
    service = SalesInvoiceService(db)
    invoice = await service.cancel(company_id, invoice_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=SalesInvoiceRead.model_validate(invoice), message="Sales invoice cancelled")
