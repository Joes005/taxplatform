import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.audit_workflow_enums import (
    AuditFindingCategory,
    AuditFindingSeverity,
    AuditFindingStatus,
)
from app.models.user import User
from app.schemas.audit_finding import (
    AuditFindingAssignRequest,
    AuditFindingCommentCreate,
    AuditFindingCommentRead,
    AuditFindingCreate,
    AuditFindingCreateResult,
    AuditFindingEvidenceCreate,
    AuditFindingEvidenceRead,
    AuditFindingRead,
    AuditFindingRejectRequest,
    AuditFindingReopenRequest,
    AuditFindingResolveRequest,
    AuditFindingResponseCreate,
    AuditFindingResponseRead,
    AuditFindingResponseReviewRequest,
    AuditFindingUpdate,
)
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.services.audit_finding_service import AuditFindingService
from app.services.auth_service import RequestMeta

router = APIRouter(tags=["audit-findings"])


@router.post(
    "/audits/engagements/{engagement_id}/findings",
    response_model=SuccessResponse[AuditFindingCreateResult],
    status_code=201,
)
async def create_finding(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_CREATE.value)),
):
    service = AuditFindingService(db)
    finding, duplicates = await service.create(company_id, engagement_id, payload, current_user, meta)
    await db.commit()
    result = AuditFindingCreateResult(
        finding=AuditFindingRead.model_validate(finding),
        duplicate_warning=bool(duplicates),
        duplicate_finding_codes=duplicates,
    )
    return SuccessResponse(data=result, message="Finding created")


@router.get(
    "/audits/engagements/{engagement_id}/findings",
    response_model=SuccessResponse[PaginatedData[AuditFindingRead]],
)
async def list_engagement_findings(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    status: AuditFindingStatus | None = Query(default=None),
    severity: AuditFindingSeverity | None = Query(default=None),
    category: AuditFindingCategory | None = Query(default=None),
    assigned_to: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_VIEW.value)),
):
    service = AuditFindingService(db)
    items, total = await service.list_for_engagement(
        company_id,
        engagement_id,
        status=status,
        severity=severity,
        category=category,
        assigned_to=assigned_to,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    data = PaginatedData(
        items=[AuditFindingRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/audits/findings", response_model=SuccessResponse[PaginatedData[AuditFindingRead]])
async def list_company_findings(
    company_id: uuid.UUID,
    status: AuditFindingStatus | None = Query(default=None),
    assigned_to: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_VIEW.value)),
):
    service = AuditFindingService(db)
    items, total = await service.list_for_company(
        company_id, status=status, assigned_to=assigned_to, offset=(page - 1) * page_size, limit=page_size
    )
    data = PaginatedData(
        items=[AuditFindingRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/audits/findings/{finding_id}", response_model=SuccessResponse[AuditFindingRead])
async def get_finding(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_VIEW.value)),
):
    service = AuditFindingService(db)
    finding = await service.get(company_id, finding_id)
    return SuccessResponse(data=AuditFindingRead.model_validate(finding))


@router.patch("/audits/findings/{finding_id}", response_model=SuccessResponse[AuditFindingRead])
async def update_finding(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_UPDATE.value)),
):
    service = AuditFindingService(db)
    finding = await service.update(company_id, finding_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingRead.model_validate(finding), message="Finding updated")


@router.post("/audits/findings/{finding_id}/assign", response_model=SuccessResponse[AuditFindingRead])
async def assign_finding(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_ASSIGN.value)),
):
    service = AuditFindingService(db)
    finding = await service.assign(company_id, finding_id, payload.assigned_to, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingRead.model_validate(finding), message="Finding assigned")


@router.post("/audits/findings/{finding_id}/start-review", response_model=SuccessResponse[AuditFindingRead])
async def start_finding_review(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_REVIEW.value)),
):
    service = AuditFindingService(db)
    finding = await service.start_review(company_id, finding_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingRead.model_validate(finding))


@router.post("/audits/findings/{finding_id}/request-action", response_model=SuccessResponse[AuditFindingRead])
async def request_finding_action(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_UPDATE.value)),
):
    service = AuditFindingService(db)
    finding = await service.request_action(company_id, finding_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingRead.model_validate(finding))


@router.post("/audits/findings/{finding_id}/resolve", response_model=SuccessResponse[AuditFindingRead])
async def resolve_finding(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_RESOLVE.value)),
):
    service = AuditFindingService(db)
    finding = await service.resolve(company_id, finding_id, payload.resolution_summary, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingRead.model_validate(finding), message="Finding resolved")


@router.post("/audits/findings/{finding_id}/close", response_model=SuccessResponse[AuditFindingRead])
async def close_finding(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_RESOLVE.value)),
):
    service = AuditFindingService(db)
    finding = await service.close(company_id, finding_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingRead.model_validate(finding), message="Finding closed")


@router.post("/audits/findings/{finding_id}/reopen", response_model=SuccessResponse[AuditFindingRead])
async def reopen_finding(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingReopenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_REOPEN.value)),
):
    service = AuditFindingService(db)
    finding = await service.reopen(company_id, finding_id, payload.reason, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingRead.model_validate(finding), message="Finding reopened")


@router.post("/audits/findings/{finding_id}/reject", response_model=SuccessResponse[AuditFindingRead])
async def reject_finding(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_RESOLVE.value)),
):
    service = AuditFindingService(db)
    finding = await service.reject(company_id, finding_id, payload.reason, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingRead.model_validate(finding), message="Finding rejected")


@router.post(
    "/audits/findings/{finding_id}/comments", response_model=SuccessResponse[AuditFindingCommentRead], status_code=201
)
async def add_comment(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_UPDATE.value)),
):
    service = AuditFindingService(db)
    comment = await service.add_comment(company_id, finding_id, payload.comment, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingCommentRead.model_validate(comment), message="Comment added")


@router.get("/audits/findings/{finding_id}/comments", response_model=SuccessResponse[list[AuditFindingCommentRead]])
async def list_comments(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_VIEW.value)),
):
    service = AuditFindingService(db)
    comments = await service.list_comments(company_id, finding_id)
    return SuccessResponse(data=[AuditFindingCommentRead.model_validate(c) for c in comments])


@router.post(
    "/audits/findings/{finding_id}/evidence", response_model=SuccessResponse[AuditFindingEvidenceRead], status_code=201
)
async def add_evidence(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingEvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_EVIDENCE_MANAGE.value)),
):
    service = AuditFindingService(db)
    evidence = await service.add_evidence(
        company_id, finding_id, payload.document_id, payload.description, current_user, meta
    )
    await db.commit()
    return SuccessResponse(data=AuditFindingEvidenceRead.model_validate(evidence), message="Evidence added")


@router.get("/audits/findings/{finding_id}/evidence", response_model=SuccessResponse[list[AuditFindingEvidenceRead]])
async def list_evidence(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_VIEW.value)),
):
    service = AuditFindingService(db)
    evidence = await service.list_evidence(company_id, finding_id)
    return SuccessResponse(data=[AuditFindingEvidenceRead.model_validate(e) for e in evidence])


@router.delete("/audits/findings/{finding_id}/evidence/{evidence_id}", response_model=SuccessResponse[None])
async def remove_evidence(
    finding_id: uuid.UUID,
    evidence_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_EVIDENCE_MANAGE.value)),
):
    service = AuditFindingService(db)
    await service.remove_evidence(company_id, finding_id, evidence_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=None, message="Evidence removed")


@router.post(
    "/audits/findings/{finding_id}/responses", response_model=SuccessResponse[AuditFindingResponseRead], status_code=201
)
async def submit_response(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_RESPOND.value)),
):
    service = AuditFindingService(db)
    response = await service.submit_response(company_id, finding_id, payload.response_text, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditFindingResponseRead.model_validate(response), message="Response submitted")


@router.get("/audits/findings/{finding_id}/responses", response_model=SuccessResponse[list[AuditFindingResponseRead]])
async def list_responses(
    finding_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_VIEW.value)),
):
    service = AuditFindingService(db)
    responses = await service.list_responses(company_id, finding_id)
    return SuccessResponse(data=[AuditFindingResponseRead.model_validate(r) for r in responses])


@router.post(
    "/audits/findings/{finding_id}/responses/{response_id}/review",
    response_model=SuccessResponse[AuditFindingResponseRead],
)
async def review_response(
    finding_id: uuid.UUID,
    response_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditFindingResponseReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_FINDING_REVIEW.value)),
):
    service = AuditFindingService(db)
    response = await service.review_response(
        company_id, finding_id, response_id, payload.accept, payload.review_comment, current_user, meta
    )
    await db.commit()
    return SuccessResponse(data=AuditFindingResponseRead.model_validate(response), message="Response reviewed")
