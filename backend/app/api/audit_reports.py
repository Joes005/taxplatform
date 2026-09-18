import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.audit_report import AuditEngagementProgress, AuditWorkflowDashboard
from app.schemas.common import SuccessResponse
from app.services.audit_service import AuditAction, AuditService
from app.services.audit_workflow_report_service import AuditWorkflowReportService
from app.services.auth_service import RequestMeta
from app.utils.file_validation import safe_content_disposition

router = APIRouter(prefix="/audits", tags=["audit-reports"])


@router.get("/dashboard", response_model=SuccessResponse[AuditWorkflowDashboard])
async def get_dashboard(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_REPORT_VIEW.value)),
):
    service = AuditWorkflowReportService(db)
    dashboard = await service.dashboard(company_id)
    return SuccessResponse(data=dashboard)


@router.get("/engagements/{engagement_id}/progress", response_model=SuccessResponse[AuditEngagementProgress])
async def get_engagement_progress(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_REPORT_VIEW.value)),
):
    service = AuditWorkflowReportService(db)
    progress = await service.engagement_progress(company_id, engagement_id)
    return SuccessResponse(data=progress)


@router.get("/engagements/{engagement_id}/export")
async def export_engagement_findings(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_REPORT_EXPORT.value)),
):
    service = AuditWorkflowReportService(db)
    file = await service.export_engagement_findings(company_id, engagement_id, format)

    await AuditService(db).log(
        action=AuditAction.AUDIT_WORKFLOW_EXPORT_GENERATED,
        user_id=current_user.id,
        company_id=company_id,
        resource_type="audit_workflow_export",
        resource_id=file.filename,
        description=f"Audit findings report exported as {file.filename}",
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    await db.commit()

    return Response(
        content=file.content,
        media_type=file.media_type,
        headers={"Content-Disposition": safe_content_disposition(file.filename)},
    )
