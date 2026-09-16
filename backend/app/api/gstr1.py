import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.permissions import PermissionCode
from app.schemas.common import SuccessResponse
from app.schemas.gstr1 import (
    GSTR1B2BRow,
    GSTR1B2CLargeRow,
    GSTR1B2COthersRow,
    GSTR1DocumentSummaryRow,
    GSTR1HSNRow,
    GSTR1NoteRow,
    GSTR1Overview,
    GSTR1ValidationResponse,
)
from app.models.gst_enums import ValidationSeverity
from app.services.gstr1_service import GSTR1Service

router = APIRouter(prefix="/gst/return-periods/{period_id}/gstr1", tags=["gstr1"])


@router.get("", response_model=SuccessResponse[GSTR1Overview])
async def get_gstr1_overview(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR1_VIEW.value)),
):
    service = GSTR1Service(db)
    overview = await service.get_overview(company_id, period_id)
    return SuccessResponse(data=overview)


@router.get("/b2b", response_model=SuccessResponse[list[GSTR1B2BRow]])
async def get_gstr1_b2b(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR1_VIEW.value)),
):
    service = GSTR1Service(db)
    return SuccessResponse(data=await service.get_b2b(company_id, period_id))


@router.get("/b2c-large", response_model=SuccessResponse[list[GSTR1B2CLargeRow]])
async def get_gstr1_b2c_large(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR1_VIEW.value)),
):
    service = GSTR1Service(db)
    return SuccessResponse(data=await service.get_b2c_large(company_id, period_id))


@router.get("/b2c-others", response_model=SuccessResponse[list[GSTR1B2COthersRow]])
async def get_gstr1_b2c_others(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR1_VIEW.value)),
):
    service = GSTR1Service(db)
    return SuccessResponse(data=await service.get_b2c_others(company_id, period_id))


@router.get("/exports", response_model=SuccessResponse[list])
async def get_gstr1_exports(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR1_VIEW.value)),
):
    service = GSTR1Service(db)
    return SuccessResponse(data=await service.get_exports(company_id, period_id))


@router.get("/credit-notes", response_model=SuccessResponse[list[GSTR1NoteRow]])
async def get_gstr1_credit_notes(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR1_VIEW.value)),
):
    service = GSTR1Service(db)
    return SuccessResponse(data=await service.get_credit_notes(company_id, period_id))


@router.get("/debit-notes", response_model=SuccessResponse[list[GSTR1NoteRow]])
async def get_gstr1_debit_notes(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR1_VIEW.value)),
):
    service = GSTR1Service(db)
    return SuccessResponse(data=await service.get_debit_notes(company_id, period_id))


@router.get("/hsn", response_model=SuccessResponse[list[GSTR1HSNRow]])
async def get_gstr1_hsn_summary(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR1_VIEW.value)),
):
    service = GSTR1Service(db)
    return SuccessResponse(data=await service.get_hsn_summary(company_id, period_id))


@router.get("/documents", response_model=SuccessResponse[list[GSTR1DocumentSummaryRow]])
async def get_gstr1_document_summary(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR1_VIEW.value)),
):
    service = GSTR1Service(db)
    return SuccessResponse(data=await service.get_document_summary(company_id, period_id))


@router.get("/validation", response_model=SuccessResponse[GSTR1ValidationResponse])
async def get_gstr1_validation(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_VALIDATE.value)),
):
    service = GSTR1Service(db)
    findings = await service.validate(company_id, period_id)
    response = GSTR1ValidationResponse(
        findings=findings,
        error_count=sum(1 for f in findings if f.severity == ValidationSeverity.ERROR),
        warning_count=sum(1 for f in findings if f.severity == ValidationSeverity.WARNING),
    )
    return SuccessResponse(data=response)
