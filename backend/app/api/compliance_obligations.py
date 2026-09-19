import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.compliance_enums import ComplianceCategory, ComplianceModule
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.compliance_obligation import (
    ComplianceObligationCreate,
    ComplianceObligationRead,
    ComplianceObligationUpdate,
    GenerateTaskRequest,
)
from app.schemas.compliance_task import ComplianceTaskRead
from app.services.auth_service import RequestMeta
from app.services.compliance_obligation_service import ComplianceObligationService
from app.services.compliance_task_service import is_overdue

router = APIRouter(prefix="/compliance/obligations", tags=["compliance-obligations"])


@router.post("", response_model=SuccessResponse[ComplianceObligationRead], status_code=201)
async def create_obligation(
    company_id: uuid.UUID,
    payload: ComplianceObligationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    obligation = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ComplianceObligationRead.model_validate(obligation), message="Obligation created")


@router.get("", response_model=SuccessResponse[PaginatedData[ComplianceObligationRead]])
async def list_obligations(
    company_id: uuid.UUID,
    category: ComplianceCategory | None = Query(default=None),
    module: ComplianceModule | None = Query(default=None),
    active_only: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceObligationService(db)
    items, total = await service.list_for_company(
        company_id, category=category, module=module, active_only=active_only, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[ComplianceObligationRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{obligation_id}", response_model=SuccessResponse[ComplianceObligationRead])
async def get_obligation(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceObligationService(db)
    obligation = await service.get(company_id, obligation_id)
    return SuccessResponse(data=ComplianceObligationRead.model_validate(obligation))


@router.patch("/{obligation_id}", response_model=SuccessResponse[ComplianceObligationRead])
async def update_obligation(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ComplianceObligationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    obligation = await service.update(company_id, obligation_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ComplianceObligationRead.model_validate(obligation), message="Obligation updated")


@router.post("/{obligation_id}/generate-task", response_model=SuccessResponse[ComplianceTaskRead], status_code=201)
async def generate_task(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: GenerateTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    task = await service.generate_task(company_id, obligation_id, payload, current_user, meta)
    await db.commit()
    read = ComplianceTaskRead.model_validate(task)
    read.is_overdue = is_overdue(task)
    return SuccessResponse(data=read, message="Task generated from obligation")
