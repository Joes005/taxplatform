import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.bank_reports import MatchReportRow, UnmatchedBankTransactionRow, UnmatchedBookTransactionRow
from app.schemas.common import SuccessResponse
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.bank_export_service import BankExportService, ExportFile
from app.services.bank_report_service import BankReportService
from app.utils.file_validation import safe_content_disposition

router = APIRouter(prefix="/bank/reports", tags=["bank-reports"])


@router.get("/unmatched-bank-transactions", response_model=SuccessResponse[list[UnmatchedBankTransactionRow]])
async def get_unmatched_bank_transactions(
    company_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    period_start: str = Query(...),
    period_end: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_REPORT_VIEW.value)),
):
    from datetime import date as _date

    service = BankReportService(db)
    rows = await service.unmatched_bank_transactions(
        company_id, bank_account_id,
        period_start=_date.fromisoformat(period_start), period_end=_date.fromisoformat(period_end),
    )
    return SuccessResponse(data=rows)


@router.get("/unmatched-book-transactions", response_model=SuccessResponse[list[UnmatchedBookTransactionRow]])
async def get_unmatched_book_transactions(
    company_id: uuid.UUID,
    ledger_id: uuid.UUID,
    period_start: str = Query(...),
    period_end: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_REPORT_VIEW.value)),
):
    from datetime import date as _date

    service = BankReportService(db)
    rows = await service.unmatched_book_transactions(
        company_id, ledger_id,
        period_start=_date.fromisoformat(period_start), period_end=_date.fromisoformat(period_end),
    )
    return SuccessResponse(data=rows)


@router.get("/matches", response_model=SuccessResponse[list[MatchReportRow]])
async def get_matching_report(
    company_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    period_start: str = Query(...),
    period_end: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_REPORT_VIEW.value)),
):
    from datetime import date as _date

    service = BankReportService(db)
    rows = await service.matching_report(
        company_id, bank_account_id,
        period_start=_date.fromisoformat(period_start), period_end=_date.fromisoformat(period_end),
    )
    return SuccessResponse(data=rows)


@router.get("/reconciliations/{reconciliation_id}/export")
async def export_reconciliation_report(
    reconciliation_id: uuid.UUID,
    company_id: uuid.UUID,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_REPORT_EXPORT.value)),
):
    service = BankExportService(db)
    file: ExportFile = await service.export_reconciliation(company_id, reconciliation_id, format)

    await AuditService(db).log(
        action=AuditAction.BANK_EXPORT_GENERATED,
        user_id=current_user.id,
        company_id=company_id,
        resource_type="bank_export",
        resource_id=file.filename,
        description=f"Bank reconciliation report exported as {file.filename}",
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    await db.commit()

    return Response(
        content=file.content,
        media_type=file.media_type,
        headers={"Content-Disposition": safe_content_disposition(file.filename)},
    )
