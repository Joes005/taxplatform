import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    get_request_meta,
    require_any_permission,
    require_permission,
)
from app.core.permissions import PermissionCode
from app.models.compliance_enums import (
    ComplianceCategory,
    ComplianceModule,
    ComplianceObligationStatus,
    ReadinessStatus,
)
from app.models.compliance_obligation import ComplianceObligation
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.compliance_obligation import (
    ComplianceControlCenterSummaryRead,
    ComplianceHealthRead,
    ComplianceObligationCreate,
    ComplianceObligationRead,
    ComplianceObligationUpdate,
    GenerateTaskRequest,
    ObligationAssignRequest,
    ObligationEvidenceCreate,
    ObligationEvidenceRead,
    ObligationReopenRequest,
    ObligationReviewActionRequest,
    ReadinessResultRead,
)
from app.schemas.compliance_task import ComplianceTaskRead
from app.services.auth_service import RequestMeta
from app.services.compliance_health_service import ComplianceHealthService
from app.services.compliance_obligation_service import ComplianceObligationService
from app.services.compliance_task_service import is_overdue

router = APIRouter(prefix="/compliance", tags=["compliance-control-center"])


def _to_obligation_read(ob: ComplianceObligation) -> ComplianceObligationRead:
    read = ComplianceObligationRead.model_validate(ob)
    today = date.today()
    read.is_overdue = (
        ob.status == ComplianceObligationStatus.OVERDUE
        or (ob.due_date < today and ob.status not in [
            ComplianceObligationStatus.COMPLETED,
            ComplianceObligationStatus.FULFILLED,
            ComplianceObligationStatus.CANCELLED,
        ])
    )
    return read


@router.get("/control-center", response_model=SuccessResponse[ComplianceControlCenterSummaryRead])
async def get_control_center_summary(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    """Unified Control Center summary aggregating health and obligation metrics (PHASE13 §16)."""
    today = date.today()
    due_soon_threshold = today + timedelta(days=7)

    # Health
    health_svc = ComplianceHealthService(db)
    health_res = await health_svc.compute_company_health(company_id)

    # Obligation counts
    closed = [
        ComplianceObligationStatus.COMPLETED,
        ComplianceObligationStatus.FULFILLED,
        ComplianceObligationStatus.CANCELLED,
    ]

    total_q = select(func.count(ComplianceObligation.id)).where(
        ComplianceObligation.company_id == company_id,
        ComplianceObligation.active.is_(True),
    )
    total_obs = (await db.execute(total_q)).scalar_one()

    due_soon_q = select(func.count(ComplianceObligation.id)).where(
        ComplianceObligation.company_id == company_id,
        ComplianceObligation.active.is_(True),
        ComplianceObligation.status.notin_(closed),
        ComplianceObligation.due_date >= today,
        ComplianceObligation.due_date <= due_soon_threshold,
    )
    due_soon_obs = (await db.execute(due_soon_q)).scalar_one()

    overdue_q = select(func.count(ComplianceObligation.id)).where(
        ComplianceObligation.company_id == company_id,
        ComplianceObligation.active.is_(True),
        ComplianceObligation.status.notin_(closed),
        or_(
            ComplianceObligation.status == ComplianceObligationStatus.OVERDUE,
            ComplianceObligation.due_date < today,
        ),
    )
    overdue_obs = (await db.execute(overdue_q)).scalar_one()

    blocked_q = select(func.count(ComplianceObligation.id)).where(
        ComplianceObligation.company_id == company_id,
        ComplianceObligation.active.is_(True),
        or_(
            ComplianceObligation.status == ComplianceObligationStatus.BLOCKED,
            ComplianceObligation.readiness_status == ReadinessStatus.BLOCKED.value,
        ),
    )
    blocked_obs = (await db.execute(blocked_q)).scalar_one()

    awaiting_review_q = select(func.count(ComplianceObligation.id)).where(
        ComplianceObligation.company_id == company_id,
        ComplianceObligation.active.is_(True),
        ComplianceObligation.status.in_([
            ComplianceObligationStatus.UNDER_REVIEW,
            ComplianceObligationStatus.READY_FOR_REVIEW,
        ]),
    )
    awaiting_review_obs = (await db.execute(awaiting_review_q)).scalar_one()

    completed_q = select(func.count(ComplianceObligation.id)).where(
        ComplianceObligation.company_id == company_id,
        ComplianceObligation.status.in_([
            ComplianceObligationStatus.COMPLETED,
            ComplianceObligationStatus.FULFILLED,
        ]),
    )
    completed_obs = (await db.execute(completed_q)).scalar_one()

    summary_data = ComplianceControlCenterSummaryRead(
        total_obligations=total_obs,
        due_soon=due_soon_obs,
        overdue=overdue_obs,
        blocked=blocked_obs,
        awaiting_review=awaiting_review_obs,
        completed=completed_obs,
        health=ComplianceHealthRead(
            health_status=health_res.health_status.value,
            score=health_res.score,
            summary=health_res.summary,
            reasons=health_res.reasons,
            dimensions=health_res.dimensions,
        ),
    )
    return SuccessResponse(data=summary_data)


@router.get("/health", response_model=SuccessResponse[ComplianceHealthRead])
async def get_compliance_health(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    """Deterministic company compliance health with detailed breakdown (PHASE13 §9)."""
    health_svc = ComplianceHealthService(db)
    result = await health_svc.compute_company_health(company_id)
    return SuccessResponse(
        data=ComplianceHealthRead(
            health_status=result.health_status.value,
            score=result.score,
            summary=result.summary,
            reasons=result.reasons,
            dimensions=result.dimensions,
        )
    )


@router.post("/obligations", response_model=SuccessResponse[ComplianceObligationRead], status_code=status.HTTP_201_CREATED)
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
    data = _to_obligation_read(obligation)
    await db.commit()
    return SuccessResponse(data=data, message="Obligation created")


@router.get("/obligations", response_model=SuccessResponse[PaginatedData[ComplianceObligationRead]])
async def list_obligations(
    company_id: uuid.UUID,
    category: ComplianceCategory | None = Query(default=None),
    module: ComplianceModule | None = Query(default=None),
    status: ComplianceObligationStatus | None = Query(default=None),
    readiness_status: str | None = Query(default=None),
    assigned_to: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    overdue_only: bool = Query(default=False),
    active_only: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceObligationService(db)
    items, total = await service.list_for_company(
        company_id,
        category=category,
        module=module,
        status=status,
        readiness_status=readiness_status,
        assigned_to=assigned_to,
        search=search,
        overdue_only=overdue_only,
        active_only=active_only,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[_to_obligation_read(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/obligations/{obligation_id}", response_model=SuccessResponse[ComplianceObligationRead])
async def get_obligation(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceObligationService(db)
    obligation = await service.get(company_id, obligation_id)
    return SuccessResponse(data=_to_obligation_read(obligation))


@router.patch("/obligations/{obligation_id}", response_model=SuccessResponse[ComplianceObligationRead])
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
    data = _to_obligation_read(obligation)
    await db.commit()
    return SuccessResponse(data=data, message="Obligation updated")


@router.post("/obligations/{obligation_id}/assign", response_model=SuccessResponse[ComplianceObligationRead])
async def assign_obligation(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ObligationAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_any_permission(PermissionCode.COMPLIANCE_TASK_ASSIGN.value, PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    obligation = await service.assign(
        company_id,
        obligation_id,
        assigned_to=payload.assigned_to,
        reviewer_id=payload.reviewer_id,
        current_user=current_user,
        meta=meta,
    )
    data = _to_obligation_read(obligation)
    await db.commit()
    return SuccessResponse(data=data, message="Obligation assigned")


@router.post("/obligations/{obligation_id}/readiness", response_model=SuccessResponse[ReadinessResultRead])
async def run_obligation_readiness(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceObligationService(db)
    result = await service.run_readiness(company_id, obligation_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ReadinessResultRead.model_validate(result.to_dict()))


@router.post("/obligations/{obligation_id}/submit-review", response_model=SuccessResponse[ComplianceObligationRead])
async def submit_obligation_review(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ObligationReviewActionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_any_permission(PermissionCode.COMPLIANCE_TASK_COMPLETE.value, PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    notes = payload.review_notes if payload else None
    obligation = await service.submit_review(company_id, obligation_id, review_notes=notes, current_user=current_user, meta=meta)
    data = _to_obligation_read(obligation)
    await db.commit()
    return SuccessResponse(data=data, message="Obligation submitted for review")


@router.post("/obligations/{obligation_id}/approve", response_model=SuccessResponse[ComplianceObligationRead])
async def approve_obligation(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ObligationReviewActionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_any_permission(PermissionCode.COMPLIANCE_TASK_VERIFY.value, PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    notes = payload.review_notes if payload else None
    obligation = await service.approve(company_id, obligation_id, review_notes=notes, current_user=current_user, meta=meta)
    data = _to_obligation_read(obligation)
    await db.commit()
    return SuccessResponse(data=data, message="Obligation approved")


@router.post("/obligations/{obligation_id}/reject", response_model=SuccessResponse[ComplianceObligationRead])
async def reject_obligation(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ObligationReviewActionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_any_permission(PermissionCode.COMPLIANCE_TASK_REVIEW.value, PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    notes = payload.review_notes if payload else None
    obligation = await service.reject(company_id, obligation_id, review_notes=notes, current_user=current_user, meta=meta)
    data = _to_obligation_read(obligation)
    await db.commit()
    return SuccessResponse(data=data, message="Obligation returned for changes")


@router.post("/obligations/{obligation_id}/complete", response_model=SuccessResponse[ComplianceObligationRead])
async def complete_obligation(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ObligationReviewActionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_any_permission(PermissionCode.COMPLIANCE_TASK_COMPLETE.value, PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    notes = payload.review_notes if payload else None
    obligation = await service.complete(company_id, obligation_id, completion_notes=notes, current_user=current_user, meta=meta)
    data = _to_obligation_read(obligation)
    await db.commit()
    return SuccessResponse(data=data, message="Obligation completed")


@router.post("/obligations/{obligation_id}/reopen", response_model=SuccessResponse[ComplianceObligationRead])
async def reopen_obligation(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ObligationReopenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    obligation = await service.reopen(company_id, obligation_id, reason=payload.reason, current_user=current_user, meta=meta)
    data = _to_obligation_read(obligation)
    await db.commit()
    return SuccessResponse(data=data, message="Obligation reopened")


@router.post("/obligations/{obligation_id}/evidence", response_model=SuccessResponse[ObligationEvidenceRead], status_code=status.HTTP_201_CREATED)
async def attach_obligation_evidence(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ObligationEvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_any_permission(PermissionCode.COMPLIANCE_TASK_UPDATE.value, PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    evidence = await service.attach_evidence(
        company_id,
        obligation_id,
        document_id=payload.document_id,
        description=payload.description,
        current_user=current_user,
        meta=meta,
    )
    data = ObligationEvidenceRead.model_validate(evidence)
    await db.commit()
    return SuccessResponse(data=data, message="Evidence attached")


@router.get("/obligations/{obligation_id}/evidence", response_model=SuccessResponse[list[ObligationEvidenceRead]])
async def list_obligation_evidence(
    obligation_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceObligationService(db)
    evidence_list = await service.list_evidence(company_id, obligation_id)
    return SuccessResponse(data=[ObligationEvidenceRead.model_validate(e) for e in evidence_list])


@router.delete("/obligations/{obligation_id}/evidence/{evidence_id}", response_model=SuccessResponse[dict])
async def remove_obligation_evidence(
    obligation_id: uuid.UUID,
    evidence_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_any_permission(PermissionCode.COMPLIANCE_TASK_UPDATE.value, PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    service = ComplianceObligationService(db)
    await service.remove_evidence(company_id, obligation_id, evidence_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data={"deleted": True}, message="Evidence removed")


@router.post("/obligations/{obligation_id}/generate-task", response_model=SuccessResponse[ComplianceTaskRead], status_code=status.HTTP_201_CREATED)
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


@router.post("/obligations/sweep-overdue", response_model=SuccessResponse[dict])
async def sweep_overdue_obligations(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_UPDATE.value)),
):
    service = ComplianceObligationService(db)
    count = await service.sweep_overdue(company_id, current_user)
    await db.commit()
    return SuccessResponse(data={"marked_overdue": count}, message=f"{count} obligation(s) marked overdue")
