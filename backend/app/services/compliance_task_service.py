"""Compliance task lifecycle (PHASE9 §4, §12-13, §43-45). Status
transitions are enforced entirely by the `_TRANSITIONS` lookup table below
— the same `(from_status, action) -> to_status` pattern already proven
for `AuditEngagementStatus`/`BankReconciliationStatus`/
`TaxComputationStatus` — so an invalid jump (e.g. `PENDING -> VERIFIED`)
is refused by construction rather than by remembering to add a check.
`OVERDUE` is an overlay `mark_overdue()` applies to an open task past its
due date; every forward action a task's underlying state supported still
applies from it (PHASE9 §16).
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.compliance_enums import ComplianceTaskStatus, NotificationSeverity, NotificationType
from app.models.compliance_task import ComplianceTask, ComplianceTaskComment, ComplianceTaskEvidence
from app.models.user import User
from app.repositories.compliance_obligation_repository import ComplianceObligationRepository
from app.repositories.compliance_task_repository import (
    ComplianceTaskCommentRepository,
    ComplianceTaskEvidenceRepository,
    ComplianceTaskRepository,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.membership_repository import MembershipRepository
from app.schemas.compliance_task import ComplianceTaskCreate, ComplianceTaskUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.notification_service import NotificationService

_TRANSITIONS: dict[tuple[ComplianceTaskStatus, str], ComplianceTaskStatus] = {
    (ComplianceTaskStatus.PENDING, "start"): ComplianceTaskStatus.IN_PROGRESS,
    (ComplianceTaskStatus.PENDING, "cancel"): ComplianceTaskStatus.CANCELLED,
    (ComplianceTaskStatus.OVERDUE, "start"): ComplianceTaskStatus.IN_PROGRESS,
    (ComplianceTaskStatus.OVERDUE, "submit_review"): ComplianceTaskStatus.PENDING_REVIEW,
    (ComplianceTaskStatus.OVERDUE, "complete"): ComplianceTaskStatus.COMPLETED,
    (ComplianceTaskStatus.OVERDUE, "cancel"): ComplianceTaskStatus.CANCELLED,
    (ComplianceTaskStatus.IN_PROGRESS, "submit_review"): ComplianceTaskStatus.PENDING_REVIEW,
    (ComplianceTaskStatus.IN_PROGRESS, "complete"): ComplianceTaskStatus.COMPLETED,
    (ComplianceTaskStatus.IN_PROGRESS, "cancel"): ComplianceTaskStatus.CANCELLED,
    (ComplianceTaskStatus.PENDING_REVIEW, "verify"): ComplianceTaskStatus.VERIFIED,
    (ComplianceTaskStatus.PENDING_REVIEW, "return_for_changes"): ComplianceTaskStatus.IN_PROGRESS,
    (ComplianceTaskStatus.COMPLETED, "verify"): ComplianceTaskStatus.VERIFIED,
    (ComplianceTaskStatus.COMPLETED, "lock"): ComplianceTaskStatus.LOCKED,
    (ComplianceTaskStatus.VERIFIED, "lock"): ComplianceTaskStatus.LOCKED,
}

_AUDIT_ACTION_BY_ACTION = {
    "start": AuditAction.COMPLIANCE_TASK_STARTED,
    "submit_review": AuditAction.COMPLIANCE_TASK_SUBMITTED,
    "complete": AuditAction.COMPLIANCE_TASK_COMPLETED,
    "verify": AuditAction.COMPLIANCE_TASK_VERIFIED,
    "return_for_changes": AuditAction.COMPLIANCE_TASK_RETURNED,
    "cancel": AuditAction.COMPLIANCE_TASK_CANCELLED,
    "lock": AuditAction.COMPLIANCE_TASK_LOCKED,
}

_OPEN_STATUSES = {
    ComplianceTaskStatus.PENDING,
    ComplianceTaskStatus.IN_PROGRESS,
    ComplianceTaskStatus.PENDING_REVIEW,
    ComplianceTaskStatus.OVERDUE,
}


def is_overdue(task: ComplianceTask, *, today: date | None = None) -> bool:
    today = today or date.today()
    return task.due_date < today and task.status in _OPEN_STATUSES


class ComplianceTaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ComplianceTaskRepository(db)
        self.obligations = ComplianceObligationRepository(db)
        self.comments = ComplianceTaskCommentRepository(db)
        self.evidence_repo = ComplianceTaskEvidenceRepository(db)
        self.memberships = MembershipRepository(db)
        self.documents = DocumentRepository(db)
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)

    async def _require_company_member(self, company_id: uuid.UUID, user_id: uuid.UUID | None, field: str) -> None:
        if user_id is None:
            return
        membership = await self.memberships.get_active_membership(user_id=user_id, company_id=company_id)
        if membership is None:
            raise ValidationAppError(
                f"The user given for {field} does not have active access to this company",
                code="COMPLIANCE_USER_NOT_A_COMPANY_MEMBER",
            )

    async def create(
        self, company_id: uuid.UUID, payload: ComplianceTaskCreate, current_user: User, meta: RequestMeta
    ) -> ComplianceTask:
        if payload.obligation_id is not None:
            obligation = await self.obligations.get_by_id_for_company(payload.obligation_id, company_id)
            if obligation is None:
                raise ValidationAppError("Obligation not found for this company", code="COMPLIANCE_OBLIGATION_NOT_FOUND")

        await self._require_company_member(company_id, payload.assigned_to, "assigned_to")
        await self._require_company_member(company_id, payload.reviewer_id, "reviewer_id")

        task = ComplianceTask(company_id=company_id, created_by=current_user.id, **payload.model_dump())
        await self.repo.create(task)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_TASK_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_task",
            resource_id=str(task.id),
            description=f"Compliance task created: {task.title}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        if task.assigned_to is not None:
            await self.notifications.notify(
                company_id=company_id,
                user_id=task.assigned_to,
                notification_type=NotificationType.TASK_ASSIGNED,
                title="New compliance task assigned",
                message=f"You've been assigned: {task.title} (due {task.due_date})",
                entity_type="compliance_task",
                entity_id=task.id,
                dedupe=False,
            )
        return task

    async def get(self, company_id: uuid.UUID, task_id: uuid.UUID) -> ComplianceTask:
        task = await self.repo.get_by_id_for_company(task_id, company_id)
        if task is None:
            raise NotFoundError("Compliance task not found", code="COMPLIANCE_TASK_NOT_FOUND")
        return task

    async def list_for_company(self, company_id: uuid.UUID, **filters):
        return await self.repo.list_for_company(company_id, **filters)

    async def update(
        self, company_id: uuid.UUID, task_id: uuid.UUID, payload: ComplianceTaskUpdate, current_user: User, meta: RequestMeta
    ) -> ComplianceTask:
        task = await self.get(company_id, task_id)
        if task.status == ComplianceTaskStatus.LOCKED:
            raise ConflictError("This task is locked and cannot be modified", code="COMPLIANCE_TASK_LOCKED")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(task, field, value)

        await self.db.flush()
        await self.db.refresh(task)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_TASK_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_task",
            resource_id=str(task.id),
            description=f"Compliance task updated: {task.title}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return task

    async def delete(self, company_id: uuid.UUID, task_id: uuid.UUID) -> None:
        task = await self.get(company_id, task_id)
        if task.status == ComplianceTaskStatus.LOCKED:
            raise ConflictError("This task is locked and cannot be deleted", code="COMPLIANCE_TASK_LOCKED")
        await self.db.delete(task)
        await self.db.flush()

    async def assign(
        self, company_id: uuid.UUID, task_id: uuid.UUID, assigned_to: uuid.UUID | None, reviewer_id: uuid.UUID | None, current_user: User, meta: RequestMeta
    ) -> ComplianceTask:
        task = await self.get(company_id, task_id)
        if task.status == ComplianceTaskStatus.LOCKED:
            raise ConflictError("This task is locked and cannot be modified", code="COMPLIANCE_TASK_LOCKED")

        await self._require_company_member(company_id, assigned_to, "assigned_to")
        await self._require_company_member(company_id, reviewer_id, "reviewer_id")

        previous_assignee = task.assigned_to
        if assigned_to is not None:
            task.assigned_to = assigned_to
        if reviewer_id is not None:
            task.reviewer_id = reviewer_id
        await self.db.flush()
        await self.db.refresh(task)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_TASK_ASSIGNED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_task",
            resource_id=str(task.id),
            description=f"Compliance task assigned: {task.title}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        if task.assigned_to is not None:
            reassigned = previous_assignee is not None and previous_assignee != task.assigned_to
            await self.notifications.notify(
                company_id=company_id,
                user_id=task.assigned_to,
                notification_type=NotificationType.TASK_REASSIGNED if reassigned else NotificationType.TASK_ASSIGNED,
                title="Compliance task reassigned to you" if reassigned else "New compliance task assigned",
                message=f"{task.title} (due {task.due_date})",
                entity_type="compliance_task",
                entity_id=task.id,
                dedupe=False,
            )
        return task

    async def _transition(
        self, company_id: uuid.UUID, task_id: uuid.UUID, action: str, current_user: User, meta: RequestMeta, *, notes: str | None = None
    ) -> ComplianceTask:
        task = await self.get(company_id, task_id)
        key = (task.status, action)
        if key not in _TRANSITIONS:
            raise ConflictError(
                f"Cannot {action.replace('_', ' ')} a task in status {task.status.value}",
                code="INVALID_COMPLIANCE_TASK_TRANSITION",
            )

        if action == "submit_review" and task.reviewer_id is None:
            raise ValidationAppError(
                "A reviewer must be assigned before this task can be submitted for review",
                code="COMPLIANCE_TASK_REVIEWER_REQUIRED",
            )

        task.status = _TRANSITIONS[key]
        now = datetime.now(timezone.utc)
        if action in ("complete",):
            task.completed_at = now
            if notes:
                task.completion_notes = notes
        if action == "verify":
            task.verified_at = now
            if task.completed_at is None:
                task.completed_at = now

        await self.db.flush()
        await self.db.refresh(task)

        await self.audit.log(
            action=_AUDIT_ACTION_BY_ACTION[action],
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_task",
            resource_id=str(task.id),
            description=f"Compliance task {task.title!r} moved to {task.status.value}"
            + (f": {notes}" if notes else ""),
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        if action == "submit_review" and task.reviewer_id is not None:
            await self.notifications.notify(
                company_id=company_id,
                user_id=task.reviewer_id,
                notification_type=NotificationType.TASK_REVIEW_REQUIRED,
                title="Compliance task ready for review",
                message=f"{task.title} is ready for your review",
                entity_type="compliance_task",
                entity_id=task.id,
            )
        elif action == "complete" and task.assigned_to is not None:
            await self.notifications.notify(
                company_id=company_id,
                user_id=task.created_by,
                notification_type=NotificationType.TASK_COMPLETED,
                title="Compliance task completed",
                message=f"{task.title} was marked complete",
                entity_type="compliance_task",
                entity_id=task.id,
            )
        elif action == "verify" and task.assigned_to is not None:
            await self.notifications.notify(
                company_id=company_id,
                user_id=task.assigned_to,
                notification_type=NotificationType.TASK_VERIFIED,
                title="Compliance task verified",
                message=f"{task.title} has been verified",
                entity_type="compliance_task",
                entity_id=task.id,
            )
        return task

    async def start(self, company_id, task_id, current_user, meta) -> ComplianceTask:
        return await self._transition(company_id, task_id, "start", current_user, meta)

    async def submit_review(self, company_id, task_id, current_user, meta) -> ComplianceTask:
        return await self._transition(company_id, task_id, "submit_review", current_user, meta)

    async def complete(self, company_id, task_id, current_user, meta, notes: str | None = None) -> ComplianceTask:
        return await self._transition(company_id, task_id, "complete", current_user, meta, notes=notes)

    async def verify(self, company_id, task_id, current_user, meta) -> ComplianceTask:
        return await self._transition(company_id, task_id, "verify", current_user, meta)

    async def return_for_changes(self, company_id, task_id, current_user, meta, reason: str) -> ComplianceTask:
        return await self._transition(company_id, task_id, "return_for_changes", current_user, meta, notes=reason)

    async def cancel(self, company_id, task_id, current_user, meta, reason: str | None = None) -> ComplianceTask:
        return await self._transition(company_id, task_id, "cancel", current_user, meta, notes=reason)

    async def lock(self, company_id, task_id, current_user, meta) -> ComplianceTask:
        return await self._transition(company_id, task_id, "lock", current_user, meta)

    async def add_comment(
        self, company_id: uuid.UUID, task_id: uuid.UUID, comment_text: str, current_user: User, meta: RequestMeta
    ) -> ComplianceTaskComment:
        task = await self.get(company_id, task_id)
        comment = ComplianceTaskComment(
            task_id=task.id,
            company_id=company_id,
            user_id=current_user.id,
            comment=comment_text,
            created_at=datetime.now(timezone.utc),
        )
        await self.comments.create(comment)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_COMMENT_ADDED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_task",
            resource_id=str(task.id),
            description=f"Comment added on task {task.title!r}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        notify_targets = {uid for uid in (task.assigned_to, task.reviewer_id, task.created_by) if uid and uid != current_user.id}
        for target in notify_targets:
            await self.notifications.notify(
                company_id=company_id,
                user_id=target,
                notification_type=NotificationType.COMMENT_ADDED,
                title="New comment on compliance task",
                message=f"{current_user.first_name} commented on {task.title}",
                entity_type="compliance_task",
                entity_id=task.id,
                dedupe=False,
            )
        return comment

    async def list_comments(self, company_id: uuid.UUID, task_id: uuid.UUID) -> list[ComplianceTaskComment]:
        task = await self.get(company_id, task_id)
        return await self.comments.list_for_task(task.id)

    async def add_evidence(
        self, company_id: uuid.UUID, task_id: uuid.UUID, document_id: uuid.UUID, description: str | None, current_user: User, meta: RequestMeta
    ) -> ComplianceTaskEvidence:
        task = await self.get(company_id, task_id)
        document = await self.documents.get_by_id_for_company(document_id, company_id)
        if document is None:
            raise ValidationAppError("Document not found for this company", code="DOCUMENT_NOT_FOUND")

        evidence = ComplianceTaskEvidence(
            task_id=task.id,
            company_id=company_id,
            document_id=document_id,
            description=description,
            created_by=current_user.id,
            created_at=datetime.now(timezone.utc),
        )
        await self.evidence_repo.create(evidence)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_EVIDENCE_ADDED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_task",
            resource_id=str(task.id),
            description=f"Evidence attached to task {task.title!r}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return evidence

    async def remove_evidence(
        self, company_id: uuid.UUID, task_id: uuid.UUID, evidence_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> None:
        task = await self.get(company_id, task_id)
        evidence = await self.evidence_repo.get_by_id_for_company(evidence_id, company_id)
        if evidence is None or evidence.task_id != task.id:
            raise NotFoundError("Evidence not found", code="COMPLIANCE_EVIDENCE_NOT_FOUND")
        await self.evidence_repo.delete(evidence)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_EVIDENCE_REMOVED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_task",
            resource_id=str(task.id),
            description=f"Evidence removed from task {task.title!r}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

    async def list_evidence(self, company_id: uuid.UUID, task_id: uuid.UUID) -> list[ComplianceTaskEvidence]:
        task = await self.get(company_id, task_id)
        return await self.evidence_repo.list_for_task(task.id)

    async def sweep_overdue(self, company_id: uuid.UUID, current_user: User | None = None) -> int:
        """Deterministic overdue detection (PHASE9 §16) — callable on-demand
        or via the background scheduler. Updates past-due open tasks to OVERDUE
        and sends deduplicated notifications to assigned users."""
        today = date.today()
        open_tasks = await self.repo.list_open_for_sweep(company_id)
        swept = 0
        for task in open_tasks:
            if task.due_date < today and task.status != ComplianceTaskStatus.OVERDUE:
                task.status = ComplianceTaskStatus.OVERDUE
                swept += 1
                if task.assigned_to is not None:
                    await self.notifications.notify(
                        company_id=company_id,
                        user_id=task.assigned_to,
                        notification_type=NotificationType.TASK_OVERDUE,
                        title="Compliance task overdue",
                        message=f"{task.title} was due {task.due_date} and is now overdue",
                        severity=NotificationSeverity.WARNING,
                        entity_type="compliance_task",
                        entity_id=task.id,
                    )
        if swept:
            await self.audit.log(
                action=AuditAction.COMPLIANCE_TASK_UPDATED,
                user_id=current_user.id if current_user else None,
                company_id=company_id,
                resource_type="compliance_task",
                resource_id=None,
                description=f"Overdue sweep marked {swept} tasks as OVERDUE",
            )
            await self.db.flush()
        return swept
