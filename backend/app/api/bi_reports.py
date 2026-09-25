"""API Router for Phase 11: Reports & Business Intelligence."""

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.bi_reports import (
    AgeingReport,
    AnalyticsReport,
    AuditReportSummary,
    BalanceSheetReport,
    CashBankReport,
    ComplianceReportSummary,
    GeneralLedgerReport,
    GSTPeriodSummary,
    ManagementDashboardReport,
    ProfitLossReport,
    ReceivablesPayablesReport,
    TDSReportSummary,
    TrialBalanceReport,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.bi_report_service import BIReportService
from app.utils.export import ExportFile, ExportFormat
from app.utils.file_validation import safe_content_disposition

router = APIRouter(prefix="/reports", tags=["reports-business-intelligence"])


def _file_response(file: ExportFile) -> Response:
    return Response(
        content=file.content,
        media_type=file.media_type,
        headers={"Content-Disposition": safe_content_disposition(file.filename)},
    )


@router.get("/management", response_model=SuccessResponse[ManagementDashboardReport])
async def get_management_dashboard(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.DASHBOARD_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_management_dashboard(company_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/trial-balance", response_model=SuccessResponse[TrialBalanceReport])
async def get_trial_balance(
    company_id: uuid.UUID,
    as_of: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.LEDGER_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_trial_balance(company_id, as_of=as_of, date_from=date_from)
    return SuccessResponse(data=report)


@router.get("/profit-loss", response_model=SuccessResponse[ProfitLossReport])
async def get_profit_loss(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    compare_previous: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_profit_loss(
        company_id, date_from=date_from, date_to=date_to, compare_previous=compare_previous
    )
    return SuccessResponse(data=report)


@router.get("/balance-sheet", response_model=SuccessResponse[BalanceSheetReport])
async def get_balance_sheet(
    company_id: uuid.UUID,
    as_of: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_balance_sheet(company_id, as_of=as_of)
    return SuccessResponse(data=report)


@router.get("/general-ledger", response_model=SuccessResponse[GeneralLedgerReport])
async def get_general_ledger(
    company_id: uuid.UUID,
    ledger_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.LEDGER_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_general_ledger(company_id, ledger_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/receivables", response_model=SuccessResponse[ReceivablesPayablesReport])
async def get_receivables(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.CUSTOMER_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_receivables(company_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/payables", response_model=SuccessResponse[ReceivablesPayablesReport])
async def get_payables(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.VENDOR_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_payables(company_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/ageing", response_model=SuccessResponse[AgeingReport])
async def get_ageing(
    company_id: uuid.UUID,
    kind: Literal["RECEIVABLES", "PAYABLES"] = Query(default="RECEIVABLES"),
    as_of: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_ageing(company_id, kind=kind, as_of=as_of)
    return SuccessResponse(data=report)


@router.get("/sales", response_model=SuccessResponse[AnalyticsReport])
async def get_sales_analytics(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.SALES_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_sales_analytics(company_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/cash-bank", response_model=SuccessResponse[CashBankReport])
async def get_cash_bank(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_REPORT_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_cash_bank(company_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/gst", response_model=SuccessResponse[GSTPeriodSummary])
async def get_gst_summary(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GST_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_gst_summary(company_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/tds", response_model=SuccessResponse[TDSReportSummary])
async def get_tds_summary(
    company_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_REPORT_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_tds_summary(company_id, date_from=date_from, date_to=date_to)
    return SuccessResponse(data=report)


@router.get("/audit", response_model=SuccessResponse[AuditReportSummary])
async def get_audit_summary(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_REPORT_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_audit_summary(company_id)
    return SuccessResponse(data=report)


@router.get("/compliance", response_model=SuccessResponse[ComplianceReportSummary])
async def get_compliance_summary(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = BIReportService(db)
    report = await service.get_compliance_summary(company_id)
    return SuccessResponse(data=report)


@router.get("/export")
async def export_report(
    company_id: uuid.UUID,
    report_type: str = Query(...),
    format: ExportFormat = Query(default="csv"),
    as_of: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = BIReportService(db)
    file = await service.export_report(
        company_id,
        report_type,
        format,
        as_of=as_of,
        date_from=date_from,
        date_to=date_to,
    )

    await AuditService(db).log(
        action=AuditAction.REPORT_EXPORT_GENERATED,
        user_id=current_user.id,
        company_id=company_id,
        resource_type="report_export",
        resource_id=file.filename,
        description=f"{report_type} exported as {file.filename}",
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    await db.commit()

    return _file_response(file)
