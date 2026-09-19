import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.compliance_enums import ComplianceCategory, ComplianceModule, CompliancePriority, ComplianceTaskStatus
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.compliance_task import (
    ComplianceTaskAssignRequest,
    ComplianceTaskCancelRequest,
    ComplianceTaskCommentCreate,
    ComplianceTaskCommentRead,
    ComplianceTaskCompleteRequest,
    ComplianceTaskCreate,
    ComplianceTaskEvidenceCreate,
    ComplianceTaskEvidenceRead,
    ComplianceTaskRead,
    ComplianceTaskReturnRequest,
    ComplianceTaskUpdate,
)
from app.services.auth_service import RequestMeta
from app.services.compliance_task_service import ComplianceTaskService, is_overdue

router = APIRouter(prefix="/compliance/tasks", tags=["compliance-tasks"])


def _to_read(task) -> ComplianceTaskRead:
    read = ComplianceTaskRead.model_validate(task)
    read.is_overdue = is_overdue(task)
    return read


@router.post("", response_model=SuccessResponse[ComplianceTaskRead], status_code=201)
async def create_task(
    company_id: uuid.UUID,
    payload: ComplianceTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_CREATE.value)),
):
    service = ComplianceTaskService(db)
    task = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Compliance task created")


@router.get("", response_model=SuccessResponse[PaginatedData[ComplianceTaskRead]])
async def list_tasks(
    company_id: uuid.UUID,
    status: ComplianceTaskStatus | None = Query(default=None),
    category: ComplianceCategory | None = Query(default=None),
    module: ComplianceModule | None = Query(default=None),
    priority: CompliancePriority | None = Query(default=None),
    assigned_to: uuid.UUID | None = Query(default=None),
    reviewer_id: uuid.UUID | None = Query(default=None),
    due_before: date | None = Query(default=None),
    due_after: date | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceTaskService(db)
    items, total = await service.list_for_company(
        company_id,
        status=status,
        category=category,
        module=module,
        priority=priority,
        assigned_to=assigned_to,
        reviewer_id=reviewer_id,
        due_before=due_before,
        due_after=due_after,
        search=search,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    data = PaginatedData(
        items=[_to_read(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{task_id}", response_model=SuccessResponse[ComplianceTaskRead])
async def get_task(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceTaskService(db)
    task = await service.get(company_id, task_id)
    return SuccessResponse(data=_to_read(task))


@router.patch("/{task_id}", response_model=SuccessResponse[ComplianceTaskRead])
async def update_task(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ComplianceTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_UPDATE.value)),
):
    service = ComplianceTaskService(db)
    task = await service.update(company_id, task_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Compliance task updated")


@router.delete("/{task_id}", response_model=SuccessResponse[None])
async def delete_task(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_UPDATE.value)),
):
    service = ComplianceTaskService(db)
    await service.delete(company_id, task_id)
    await db.commit()
    return SuccessResponse(data=None, message="Compliance task deleted")


@router.post("/{task_id}/assign", response_model=SuccessResponse[ComplianceTaskRead])
async def assign_task(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ComplianceTaskAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_ASSIGN.value)),
):
    service = ComplianceTaskService(db)
    task = await service.assign(company_id, task_id, payload.assigned_to, payload.reviewer_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Compliance task assigned")


@router.post("/{task_id}/start", response_model=SuccessResponse[ComplianceTaskRead])
async def start_task(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_UPDATE.value)),
):
    service = ComplianceTaskService(db)
    task = await service.start(company_id, task_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Compliance task started")


@router.post("/{task_id}/submit-review", response_model=SuccessResponse[ComplianceTaskRead])
async def submit_review(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_COMPLETE.value)),
):
    service = ComplianceTaskService(db)
    task = await service.submit_review(company_id, task_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Submitted for review")


@router.post("/{task_id}/complete", response_model=SuccessResponse[ComplianceTaskRead])
async def complete_task(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ComplianceTaskCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_COMPLETE.value)),
):
    service = ComplianceTaskService(db)
    task = await service.complete(company_id, task_id, current_user, meta, payload.completion_notes)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Compliance task completed")


@router.post("/{task_id}/verify", response_model=SuccessResponse[ComplianceTaskRead])
async def verify_task(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_VERIFY.value)),
):
    service = ComplianceTaskService(db)
    task = await service.verify(company_id, task_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Compliance task verified")


@router.post("/{task_id}/return-for-changes", response_model=SuccessResponse[ComplianceTaskRead])
async def return_for_changes(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ComplianceTaskReturnRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_REVIEW.value)),
):
    service = ComplianceTaskService(db)
    task = await service.return_for_changes(company_id, task_id, current_user, meta, payload.reason)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Returned for changes")


@router.post("/{task_id}/cancel", response_model=SuccessResponse[ComplianceTaskRead])
async def cancel_task(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ComplianceTaskCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_CANCEL.value)),
):
    service = ComplianceTaskService(db)
    task = await service.cancel(company_id, task_id, current_user, meta, payload.reason)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Compliance task cancelled")


@router.post("/{task_id}/lock", response_model=SuccessResponse[ComplianceTaskRead])
async def lock_task(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_LOCK.value)),
):
    service = ComplianceTaskService(db)
    task = await service.lock(company_id, task_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read(task), message="Compliance task locked")


@router.post("/{task_id}/comments", response_model=SuccessResponse[ComplianceTaskCommentRead], status_code=201)
async def add_comment(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ComplianceTaskCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_UPDATE.value)),
):
    service = ComplianceTaskService(db)
    comment = await service.add_comment(company_id, task_id, payload.comment, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ComplianceTaskCommentRead.model_validate(comment), message="Comment added")


@router.get("/{task_id}/comments", response_model=SuccessResponse[list[ComplianceTaskCommentRead]])
async def list_comments(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceTaskService(db)
    comments = await service.list_comments(company_id, task_id)
    return SuccessResponse(data=[ComplianceTaskCommentRead.model_validate(c) for c in comments])


@router.post("/{task_id}/evidence", response_model=SuccessResponse[ComplianceTaskEvidenceRead], status_code=201)
async def add_evidence(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ComplianceTaskEvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_UPDATE.value)),
):
    service = ComplianceTaskService(db)
    evidence = await service.add_evidence(company_id, task_id, payload.document_id, payload.description, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ComplianceTaskEvidenceRead.model_validate(evidence), message="Evidence added")


@router.get("/{task_id}/evidence", response_model=SuccessResponse[list[ComplianceTaskEvidenceRead]])
async def list_evidence(
    task_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceTaskService(db)
    evidence = await service.list_evidence(company_id, task_id)
    return SuccessResponse(data=[ComplianceTaskEvidenceRead.model_validate(e) for e in evidence])


@router.delete("/{task_id}/evidence/{evidence_id}", response_model=SuccessResponse[None])
async def remove_evidence(
    task_id: uuid.UUID,
    evidence_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_TASK_UPDATE.value)),
):
    service = ComplianceTaskService(db)
    await service.remove_evidence(company_id, task_id, evidence_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=None, message="Evidence removed")
