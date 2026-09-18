import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.tds_reports import (
    TDSChallanSummaryRow,
    TDSDeducteeSummaryRow,
    TDSQuarterlySummary,
    TDSSectionSummaryRow,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.tds_export_service import ExportFile, TDSExportService
from app.services.tds_report_service import TDSReportService
from app.services.tds_return_period_service import TDSReturnPeriodService
from app.utils.file_validation import safe_content_disposition

router = APIRouter(prefix="/tds/return-periods/{period_id}/reports", tags=["tds-reports"])


@router.get("/summary", response_model=SuccessResponse[TDSQuarterlySummary])
async def get_quarterly_summary(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_REPORT_VIEW.value)),
):
    period = await TDSReturnPeriodService(db).get(company_id, period_id)
    summary = await TDSReportService(db).quarterly_summary(company_id, period.period_start, period.period_end)
    return SuccessResponse(data=summary)


@router.get("/sections", response_model=SuccessResponse[list[TDSSectionSummaryRow]])
async def get_section_summary(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_REPORT_VIEW.value)),
):
    period = await TDSReturnPeriodService(db).get(company_id, period_id)
    rows = await TDSReportService(db).section_summary(company_id, period.period_start, period.period_end)
    return SuccessResponse(data=rows)


@router.get("/deductees", response_model=SuccessResponse[list[TDSDeducteeSummaryRow]])
async def get_deductee_summary(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_REPORT_VIEW.value)),
):
    period = await TDSReturnPeriodService(db).get(company_id, period_id)
    rows = await TDSReportService(db).deductee_summary(company_id, period.period_start, period.period_end)
    return SuccessResponse(data=rows)


@router.get("/challans", response_model=SuccessResponse[list[TDSChallanSummaryRow]])
async def get_challan_summary(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_REPORT_VIEW.value)),
):
    period = await TDSReturnPeriodService(db).get(company_id, period_id)
    rows = await TDSReportService(db).challan_summary(company_id, period.financial_year_id)
    return SuccessResponse(data=rows)


async def _log_export(
    db: AsyncSession, *, company_id: uuid.UUID, current_user: User, meta: RequestMeta, report_type: str, file: ExportFile
) -> None:
    await AuditService(db).log(
        action=AuditAction.TDS_EXPORT_GENERATED,
        user_id=current_user.id,
        company_id=company_id,
        resource_type="tds_export",
        resource_id=file.filename,
        description=f"{report_type} exported as {file.filename}",
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    await db.commit()


def _file_response(file: ExportFile) -> Response:
    return Response(
        content=file.content,
        media_type=file.media_type,
        headers={"Content-Disposition": safe_content_disposition(file.filename)},
    )


@router.get("/export/quarterly")
async def export_quarterly_report(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_REPORT_EXPORT.value)),
):
    service = TDSExportService(db)
    file = await service.export_quarterly_summary(company_id, period_id, format)
    await _log_export(db, company_id=company_id, current_user=current_user, meta=meta, report_type="TDS Quarterly Summary", file=file)
    return _file_response(file)


@router.get("/export/reconciliation")
async def export_reconciliation_report(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_REPORT_EXPORT.value)),
):
    service = TDSExportService(db)
    file = await service.export_reconciliation(company_id, period_id, format)
    await _log_export(db, company_id=company_id, current_user=current_user, meta=meta, report_type="TDS Reconciliation", file=file)
    return _file_response(file)
