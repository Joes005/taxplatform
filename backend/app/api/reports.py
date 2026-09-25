import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.permissions import PermissionCode
from app.schemas.common import SuccessResponse
from app.schemas.reports import PartyOutstanding, SalesPurchaseSummary, TrialBalance
from app.services.report_service import ReportService
from app.utils.export import ExportFile, ExportFormat
from app.utils.file_validation import safe_content_disposition

router = APIRouter(prefix="/accounting/reports", tags=["accounting-reports"])


def _file_response(file: ExportFile) -> Response:
    return Response(
        content=file.content,
        media_type=file.media_type,
        headers={"Content-Disposition": safe_content_disposition(file.filename)},
    )


@router.get("/sales-summary", response_model=SuccessResponse[SalesPurchaseSummary])
async def sales_summary(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.SALES_VIEW.value)),
):
    report = await ReportService(db).sales_summary(company_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/purchase-summary", response_model=SuccessResponse[SalesPurchaseSummary])
async def purchase_summary(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.PURCHASE_VIEW.value)),
):
    report = await ReportService(db).purchase_summary(company_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/customer-outstanding", response_model=SuccessResponse[list[PartyOutstanding]])
async def customer_outstanding(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.CUSTOMER_VIEW.value)),
):
    report = await ReportService(db).customer_outstanding(company_id)
    return SuccessResponse(data=report)


@router.get("/vendor-outstanding", response_model=SuccessResponse[list[PartyOutstanding]])
async def vendor_outstanding(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.VENDOR_VIEW.value)),
):
    report = await ReportService(db).vendor_outstanding(company_id)
    return SuccessResponse(data=report)


@router.get("/trial-balance", response_model=SuccessResponse[TrialBalance])
async def trial_balance(
    company_id: uuid.UUID,
    as_of: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.LEDGER_VIEW.value)),
):
    report = await ReportService(db).trial_balance(company_id, as_of=as_of)
    return SuccessResponse(data=report)


@router.get("/sales-register/export")
async def export_sales_register(
    company_id: uuid.UUID,
    format: ExportFormat = Query(default="csv"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.SALES_VIEW.value)),
):
    service = ReportService(db)
    file = await service.export_sales_register(company_id, format, date_from=date_from, date_to=date_to)
    return _file_response(file)


@router.get("/purchase-register/export")
async def export_purchase_register(
    company_id: uuid.UUID,
    format: ExportFormat = Query(default="csv"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.PURCHASE_VIEW.value)),
):
    service = ReportService(db)
    file = await service.export_purchase_register(company_id, format, date_from=date_from, date_to=date_to)
    return _file_response(file)


@router.get("/trial-balance/export")
async def export_trial_balance(
    company_id: uuid.UUID,
    format: ExportFormat = Query(default="csv"),
    as_of: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.LEDGER_VIEW.value)),
):
    service = ReportService(db)
    file = await service.export_trial_balance(company_id, format, as_of=as_of)
    return _file_response(file)
