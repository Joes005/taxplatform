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
from app.services.income_tax_report_service import IncomeTaxReportService
from app.utils.file_validation import safe_content_disposition

router = APIRouter(prefix="/income-tax/reports", tags=["income-tax-reports"])


@router.get("/computations/{computation_id}/export")
async def export_computation(
    computation_id: uuid.UUID,
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_EXPORT.value)),
):
    service = IncomeTaxReportService(db)
    file = await service.export_computation(company_id, computation_id, format)

    await AuditService(db).log(
        action=AuditAction.INCOME_TAX_EXPORT_GENERATED,
        user_id=current_user.id,
        company_id=company_id,
        resource_type="income_tax_export",
        resource_id=file.filename,
        description=f"Income Tax computation exported as {file.filename}",
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    await db.commit()

    return Response(
        content=file.content,
        media_type=file.media_type,
        headers={"Content-Disposition": safe_content_disposition(file.filename)},
    )
