import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.gst_export_service import ExportFile, GSTExportService
from app.utils.file_validation import safe_content_disposition

router = APIRouter(prefix="/gst/return-periods/{period_id}/reports", tags=["gst-reports"])


async def _log_export(
    db: AsyncSession, *, company_id: uuid.UUID, current_user: User, meta: RequestMeta, report_type: str, file: ExportFile
) -> None:
    await AuditService(db).log(
        action=AuditAction.GST_EXPORT_GENERATED,
        user_id=current_user.id,
        company_id=company_id,
        resource_type="gst_export",
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


@router.get("/gstr1")
async def export_gstr1_report(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GSTR1_EXPORT.value)),
):
    service = GSTExportService(db)
    file = await service.export_gstr1(company_id, period_id, format)
    await _log_export(db, company_id=company_id, current_user=current_user, meta=meta, report_type="GSTR-1", file=file)
    return _file_response(file)


@router.get("/gstr3b")
async def export_gstr3b_report(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GSTR3B_EXPORT.value)),
):
    service = GSTExportService(db)
    file = await service.export_gstr3b(company_id, period_id, format)
    await _log_export(db, company_id=company_id, current_user=current_user, meta=meta, report_type="GSTR-3B", file=file)
    return _file_response(file)


@router.get("/reconciliation")
async def export_reconciliation_report(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GSTR2B_VIEW.value)),
):
    service = GSTExportService(db)
    file = await service.export_reconciliation(company_id, period_id, format)
    await _log_export(db, company_id=company_id, current_user=current_user, meta=meta, report_type="Reconciliation", file=file)
    return _file_response(file)


@router.get("/itc")
async def export_itc_report(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ITC_VIEW.value)),
):
    service = GSTExportService(db)
    file = await service.export_itc(company_id, period_id, format)
    await _log_export(db, company_id=company_id, current_user=current_user, meta=meta, report_type="ITC Summary", file=file)
    return _file_response(file)
