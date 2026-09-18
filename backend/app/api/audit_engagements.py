import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.audit_workflow_enums import AuditEngagementStatus
from app.models.user import User
from app.schemas.audit_assignment import AuditAssignmentCreate, AuditAssignmentRead
from app.schemas.audit_engagement import (
    AuditEngagementActionRequest,
    AuditEngagementCreate,
    AuditEngagementRead,
    AuditEngagementUpdate,
)
from app.schemas.audit_review import AuditSignOffCreate, AuditSignOffRead
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.services.audit_assignment_service import AuditAssignmentService
from app.services.audit_engagement_service import AuditEngagementService
from app.services.audit_review_service import AuditSignOffService
from app.services.auth_service import RequestMeta

router = APIRouter(prefix="/audits/engagements", tags=["audit-engagements"])


@router.post("", response_model=SuccessResponse[AuditEngagementRead], status_code=201)
async def create_engagement(
    company_id: uuid.UUID,
    payload: AuditEngagementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_CREATE.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Engagement created")


@router.get("", response_model=SuccessResponse[PaginatedData[AuditEngagementRead]])
async def list_engagements(
    company_id: uuid.UUID,
    status: AuditEngagementStatus | None = Query(default=None),
    financial_year_id: uuid.UUID | None = Query(default=None),
    assigned_to: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_VIEW.value)),
):
    service = AuditEngagementService(db)
    items, total = await service.list(
        company_id,
        status=status,
        financial_year_id=financial_year_id,
        assigned_to=assigned_to,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[AuditEngagementRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{engagement_id}", response_model=SuccessResponse[AuditEngagementRead])
async def get_engagement(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_VIEW.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.get(company_id, engagement_id)
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement))


@router.patch("/{engagement_id}", response_model=SuccessResponse[AuditEngagementRead])
async def update_engagement(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditEngagementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_UPDATE.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.update(company_id, engagement_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Engagement updated")


@router.post("/{engagement_id}/open", response_model=SuccessResponse[AuditEngagementRead])
async def open_engagement(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_UPDATE.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.open(company_id, engagement_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Engagement opened")


@router.post("/{engagement_id}/start-review", response_model=SuccessResponse[AuditEngagementRead])
async def start_review(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_REVIEW.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.start_review(company_id, engagement_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Review started")


@router.post("/{engagement_id}/request-client-action", response_model=SuccessResponse[AuditEngagementRead])
async def request_client_action(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditEngagementActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_UPDATE.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.request_client_action(company_id, engagement_id, current_user, meta, payload.comment)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Pending client action")


@router.post("/{engagement_id}/resume-review", response_model=SuccessResponse[AuditEngagementRead])
async def resume_review(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_UPDATE.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.resume_review(company_id, engagement_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Review resumed")


@router.post("/{engagement_id}/submit-for-review", response_model=SuccessResponse[AuditEngagementRead])
async def submit_for_review(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_UPDATE.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.submit_for_review(company_id, engagement_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Submitted for auditor review")


@router.post("/{engagement_id}/approve", response_model=SuccessResponse[AuditEngagementRead])
async def approve_engagement(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditEngagementActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_APPROVE.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.approve(company_id, engagement_id, current_user, meta, payload.comment)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Engagement approved")


@router.post("/{engagement_id}/return-for-changes", response_model=SuccessResponse[AuditEngagementRead])
async def return_for_changes(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditEngagementActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_APPROVE.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.return_for_changes(company_id, engagement_id, current_user, meta, payload.comment)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Returned for changes")


@router.post("/{engagement_id}/mark-signed-off", response_model=SuccessResponse[AuditEngagementRead])
async def mark_signed_off(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_SIGNOFF.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.sign_off_transition(company_id, engagement_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Engagement marked signed off")


@router.post("/{engagement_id}/close", response_model=SuccessResponse[AuditEngagementRead])
async def close_engagement(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_LOCK.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.close(company_id, engagement_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Engagement closed")


@router.post("/{engagement_id}/cancel", response_model=SuccessResponse[AuditEngagementRead])
async def cancel_engagement(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditEngagementActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_UPDATE.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.cancel(company_id, engagement_id, current_user, meta, payload.comment)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Engagement cancelled")


@router.post("/{engagement_id}/lock", response_model=SuccessResponse[AuditEngagementRead])
async def lock_engagement(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_LOCK.value)),
):
    service = AuditEngagementService(db)
    engagement = await service.lock(company_id, engagement_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditEngagementRead.model_validate(engagement), message="Engagement locked")


@router.post("/{engagement_id}/sign-offs", response_model=SuccessResponse[AuditSignOffRead], status_code=201)
async def create_signoff(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditSignOffCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_SIGNOFF.value)),
):
    service = AuditSignOffService(db)
    signoff = await service.create(company_id, engagement_id, payload.sign_off_type, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditSignOffRead.model_validate(signoff), message="Sign-off recorded")


@router.get("/{engagement_id}/sign-offs", response_model=SuccessResponse[list[AuditSignOffRead]])
async def list_signoffs(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_VIEW.value)),
):
    service = AuditSignOffService(db)
    signoffs = await service.list_for_engagement(company_id, engagement_id)
    return SuccessResponse(data=[AuditSignOffRead.model_validate(s) for s in signoffs])


@router.post("/{engagement_id}/assignments", response_model=SuccessResponse[AuditAssignmentRead], status_code=201)
async def create_assignment(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_ASSIGN.value)),
):
    service = AuditAssignmentService(db)
    assignment = await service.assign(
        company_id, engagement_id, payload.user_id, payload.role, current_user, meta
    )
    await db.commit()
    return SuccessResponse(data=AuditAssignmentRead.model_validate(assignment), message="User assigned")


@router.get("/{engagement_id}/assignments", response_model=SuccessResponse[list[AuditAssignmentRead]])
async def list_assignments(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_VIEW.value)),
):
    service = AuditAssignmentService(db)
    assignments = await service.list_for_engagement(company_id, engagement_id)
    return SuccessResponse(data=[AuditAssignmentRead.model_validate(a) for a in assignments])


@router.delete("/{engagement_id}/assignments/{assignment_id}", response_model=SuccessResponse[AuditAssignmentRead])
async def remove_assignment(
    engagement_id: uuid.UUID,
    assignment_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_ASSIGN.value)),
):
    service = AuditAssignmentService(db)
    assignment = await service.unassign(company_id, engagement_id, assignment_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditAssignmentRead.model_validate(assignment), message="User unassigned")
