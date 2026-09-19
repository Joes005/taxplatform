import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.compliance_enums import ComplianceCategory, ComplianceModule, CompliancePriority, ComplianceTaskStatus
from app.models.user import User
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.compliance_report_service import ComplianceReportService
from app.utils.file_validation import safe_content_disposition

router = APIRouter(prefix="/compliance/reports", tags=["compliance-reports"])


@router.get("/tasks/export")
async def export_tasks(
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    status: ComplianceTaskStatus | None = Query(default=None),
    category: ComplianceCategory | None = Query(default=None),
    module: ComplianceModule | None = Query(default=None),
    priority: CompliancePriority | None = Query(default=None),
    overdue_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_REPORT_EXPORT.value)),
):
    service = ComplianceReportService(db)
    file = await service.export_tasks(
        company_id, format, status=status, category=category, module=module, priority=priority, overdue_only=overdue_only
    )

    await AuditService(db).log(
        action=AuditAction.COMPLIANCE_EXPORT_GENERATED,
        user_id=current_user.id,
        company_id=company_id,
        resource_type="compliance_export",
        resource_id=file.filename,
        description=f"Compliance task report exported as {file.filename}",
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    await db.commit()

    return Response(
        content=file.content,
        media_type=file.media_type,
        headers={"Content-Disposition": safe_content_disposition(file.filename)},
    )
