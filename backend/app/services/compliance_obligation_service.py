"""Compliance obligation CRUD, rule-driven generation, readiness checking,
and Phase 13 full lifecycle workflow (PHASE9 §5, PHASE13 §4, §7-13).

Enforces the central lifecycle:
OBLIGATION -> SCHEDULE -> DUE DATE -> PREREQUISITES -> READINESS CHECK
-> TASK -> EVIDENCE -> REVIEW -> APPROVAL / COMPLETION -> AUDIT TRAIL.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.compliance_enums import (
    ComplianceCategory,
    ComplianceModule,
    ComplianceObligationStatus,
    NotificationSeverity,
    NotificationType,
    ReadinessStatus,
)
from app.models.compliance_obligation import ComplianceObligation
from app.models.compliance_obligation_evidence import ComplianceObligationEvidence
from app.models.compliance_task import ComplianceTask
from app.models.user import User
from app.repositories.compliance_obligation_evidence_repository import ComplianceObligationEvidenceRepository
from app.repositories.compliance_obligation_repository import ComplianceObligationRepository
from app.repositories.compliance_rule_repository import ComplianceRuleRepository
from app.repositories.compliance_task_repository import ComplianceTaskRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.membership_repository import MembershipRepository
from app.schemas.compliance_obligation import (
    ComplianceObligationCreate,
    ComplianceObligationUpdate,
    GenerateTaskRequest,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.compliance_deadline_service import compute_due_date
from app.services.compliance_readiness_service import ComplianceReadinessService, ReadinessResult
from app.services.notification_service import NotificationService

_OBLIGATION_TRANSITIONS: dict[tuple[ComplianceObligationStatus, str], ComplianceObligationStatus] = {
    (ComplianceObligationStatus.DRAFT, "assign"): ComplianceObligationStatus.ASSIGNED,
    (ComplianceObligationStatus.DRAFT, "start"): ComplianceObligationStatus.IN_PROGRESS,
    (ComplianceObligationStatus.DRAFT, "submit_review"): ComplianceObligationStatus.READY_FOR_REVIEW,
    (ComplianceObligationStatus.DRAFT, "complete"): ComplianceObligationStatus.COMPLETED,
    (ComplianceObligationStatus.DRAFT, "cancel"): ComplianceObligationStatus.CANCELLED,
    (ComplianceObligationStatus.ACTIVE, "assign"): ComplianceObligationStatus.ASSIGNED,
    (ComplianceObligationStatus.ACTIVE, "start"): ComplianceObligationStatus.IN_PROGRESS,
    (ComplianceObligationStatus.ACTIVE, "submit_review"): ComplianceObligationStatus.READY_FOR_REVIEW,
    (ComplianceObligationStatus.ACTIVE, "complete"): ComplianceObligationStatus.COMPLETED,
    (ComplianceObligationStatus.ACTIVE, "cancel"): ComplianceObligationStatus.CANCELLED,
    (ComplianceObligationStatus.ASSIGNED, "start"): ComplianceObligationStatus.IN_PROGRESS,
    (ComplianceObligationStatus.ASSIGNED, "submit_review"): ComplianceObligationStatus.READY_FOR_REVIEW,
    (ComplianceObligationStatus.ASSIGNED, "complete"): ComplianceObligationStatus.COMPLETED,
    (ComplianceObligationStatus.ASSIGNED, "reassign"): ComplianceObligationStatus.ASSIGNED,
    (ComplianceObligationStatus.ASSIGNED, "cancel"): ComplianceObligationStatus.CANCELLED,
    (ComplianceObligationStatus.IN_PROGRESS, "submit_review"): ComplianceObligationStatus.READY_FOR_REVIEW,
    (ComplianceObligationStatus.IN_PROGRESS, "complete"): ComplianceObligationStatus.COMPLETED,
    (ComplianceObligationStatus.IN_PROGRESS, "reassign"): ComplianceObligationStatus.IN_PROGRESS,
    (ComplianceObligationStatus.IN_PROGRESS, "cancel"): ComplianceObligationStatus.CANCELLED,
    (ComplianceObligationStatus.READY_FOR_REVIEW, "start_review"): ComplianceObligationStatus.UNDER_REVIEW,
    (ComplianceObligationStatus.READY_FOR_REVIEW, "submit_review"): ComplianceObligationStatus.READY_FOR_REVIEW,
    (ComplianceObligationStatus.READY_FOR_REVIEW, "approve"): ComplianceObligationStatus.APPROVED,
    (ComplianceObligationStatus.READY_FOR_REVIEW, "reject"): ComplianceObligationStatus.REJECTED,
    (ComplianceObligationStatus.READY_FOR_REVIEW, "return_for_changes"): ComplianceObligationStatus.IN_PROGRESS,
    (ComplianceObligationStatus.UNDER_REVIEW, "approve"): ComplianceObligationStatus.APPROVED,
    (ComplianceObligationStatus.UNDER_REVIEW, "reject"): ComplianceObligationStatus.REJECTED,
    (ComplianceObligationStatus.REJECTED, "start"): ComplianceObligationStatus.IN_PROGRESS,
    (ComplianceObligationStatus.REJECTED, "submit_review"): ComplianceObligationStatus.READY_FOR_REVIEW,
    (ComplianceObligationStatus.APPROVED, "complete"): ComplianceObligationStatus.COMPLETED,
    (ComplianceObligationStatus.APPROVED, "reopen"): ComplianceObligationStatus.REOPENED,
    (ComplianceObligationStatus.COMPLETED, "reopen"): ComplianceObligationStatus.REOPENED,
    (ComplianceObligationStatus.FULFILLED, "reopen"): ComplianceObligationStatus.REOPENED,
    (ComplianceObligationStatus.REOPENED, "start"): ComplianceObligationStatus.IN_PROGRESS,
    (ComplianceObligationStatus.REOPENED, "assign"): ComplianceObligationStatus.ASSIGNED,
    (ComplianceObligationStatus.REOPENED, "submit_review"): ComplianceObligationStatus.READY_FOR_REVIEW,
    (ComplianceObligationStatus.REOPENED, "complete"): ComplianceObligationStatus.COMPLETED,
    (ComplianceObligationStatus.OVERDUE, "start"): ComplianceObligationStatus.IN_PROGRESS,
    (ComplianceObligationStatus.OVERDUE, "submit_review"): ComplianceObligationStatus.READY_FOR_REVIEW,
    (ComplianceObligationStatus.OVERDUE, "complete"): ComplianceObligationStatus.COMPLETED,
    (ComplianceObligationStatus.OVERDUE, "cancel"): ComplianceObligationStatus.CANCELLED,
    (ComplianceObligationStatus.BLOCKED, "unblock"): ComplianceObligationStatus.IN_PROGRESS,
    (ComplianceObligationStatus.BLOCKED, "cancel"): ComplianceObligationStatus.CANCELLED,
}

_OPEN_OBLIGATION_STATUSES = {
    ComplianceObligationStatus.DRAFT,
    ComplianceObligationStatus.ACTIVE,
    ComplianceObligationStatus.ASSIGNED,
    ComplianceObligationStatus.IN_PROGRESS,
    ComplianceObligationStatus.READY_FOR_REVIEW,
    ComplianceObligationStatus.UNDER_REVIEW,
    ComplianceObligationStatus.REJECTED,
    ComplianceObligationStatus.BLOCKED,
    ComplianceObligationStatus.OVERDUE,
    ComplianceObligationStatus.REOPENED,
}


class ComplianceObligationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ComplianceObligationRepository(db)
        self.rules = ComplianceRuleRepository(db)
        self.tasks = ComplianceTaskRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.memberships = MembershipRepository(db)
        self.documents = DocumentRepository(db)
        self.evidence_repo = ComplianceObligationEvidenceRepository(db)
        self.readiness = ComplianceReadinessService(db)
        self.notifications = NotificationService(db)
        self.audit = AuditService(db)

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
        self, company_id: uuid.UUID, payload: ComplianceObligationCreate, current_user: User, meta: RequestMeta
    ) -> ComplianceObligation:
        if payload.financial_year_id is not None:
            if await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id) is None:
                raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")

        existing = await self.repo.get_by_natural_key(
            company_id, payload.code, payload.financial_year_id, payload.tax_period
        )
        if existing is not None:
            raise ValidationAppError(
                "An obligation for this code/financial-year/period already exists",
                code="COMPLIANCE_OBLIGATION_ALREADY_EXISTS",
            )

        if payload.assigned_to:
            await self._require_company_member(company_id, payload.assigned_to, "assigned_to")
        if payload.reviewer_id:
            await self._require_company_member(company_id, payload.reviewer_id, "reviewer_id")

        initial_status = ComplianceObligationStatus.ASSIGNED if payload.assigned_to else ComplianceObligationStatus.DRAFT

        data = payload.model_dump()
        obligation = ComplianceObligation(
            company_id=company_id,
            created_by=current_user.id,
            status=initial_status,
            **data,
        )
        await self.repo.create(obligation)

        # Initial readiness evaluation
        readiness_res = await self.readiness.evaluate_obligation(company_id, obligation)
        obligation.readiness_status = readiness_res.overall_status.value
        obligation.readiness_details = readiness_res.to_dict()
        if readiness_res.overall_status == ReadinessStatus.BLOCKED:
            obligation.status = ComplianceObligationStatus.BLOCKED

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Compliance obligation {obligation.code} created (due {obligation.due_date})",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        if payload.assigned_to:
            await self.notifications.create(
                company_id=company_id,
                user_id=payload.assigned_to,
                type=NotificationType.OBLIGATION_ASSIGNED,
                title=f"Compliance obligation assigned: {obligation.name}",
                message=f"You have been assigned compliance obligation {obligation.code} (due {obligation.due_date})",
                severity=NotificationSeverity.INFO,
                entity_type="compliance_obligation",
                entity_id=obligation.id,
            )

        await self.db.flush()
        await self.db.refresh(obligation)
        return obligation

    async def generate_from_rule(
        self,
        company_id: uuid.UUID,
        *,
        rule_code: str,
        financial_year_id: uuid.UUID | None,
        tax_period: str | None,
        period_start: date,
        period_end: date,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        existing = await self.repo.get_by_natural_key(company_id, rule_code, financial_year_id, tax_period)
        if existing is not None:
            return existing

        rule = await self.rules.get_active_version(rule_code, company_id)
        if rule is None:
            raise ValidationAppError(
                f"No active compliance rule configured for code {rule_code!r}",
                code="COMPLIANCE_RULE_NOT_CONFIGURED",
            )

        due_date = compute_due_date(rule.due_date_rule, period_start=period_start, period_end=period_end)

        obligation = ComplianceObligation(
            company_id=company_id,
            code=rule.code,
            name=rule.name,
            description=rule.description,
            category=rule.category,
            module=rule.module,
            frequency=rule.frequency,
            financial_year_id=financial_year_id,
            tax_period=tax_period,
            start_date=period_start,
            due_date=due_date,
            priority=rule.priority,
            status=ComplianceObligationStatus.ACTIVE,
            is_recurring=rule.frequency.value != "ONE_TIME",
            rule_id=rule.id,
            rule_version=rule.version,
            created_by=current_user.id,
        )
        await self.repo.create(obligation)

        # Evaluate readiness
        readiness_res = await self.readiness.evaluate_obligation(company_id, obligation)
        obligation.readiness_status = readiness_res.overall_status.value
        obligation.readiness_details = readiness_res.to_dict()

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Compliance obligation {obligation.code} generated from rule v{rule.version} (due {due_date})",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        await self.db.flush()
        await self.db.refresh(obligation)
        return obligation

    async def get(self, company_id: uuid.UUID, obligation_id: uuid.UUID) -> ComplianceObligation:
        obligation = await self.repo.get_by_id_for_company(obligation_id, company_id)
        if obligation is None:
            raise NotFoundError("Compliance obligation not found", code="COMPLIANCE_OBLIGATION_NOT_FOUND")
        return obligation

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        category: ComplianceCategory | None = None,
        module: ComplianceModule | None = None,
        status: ComplianceObligationStatus | None = None,
        readiness_status: str | None = None,
        assigned_to: uuid.UUID | None = None,
        search: str | None = None,
        overdue_only: bool = False,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ComplianceObligation], int]:
        return await self.repo.list_for_company(
            company_id,
            category=category,
            module=module,
            status=status,
            readiness_status=readiness_status,
            assigned_to=assigned_to,
            search=search,
            overdue_only=overdue_only,
            active_only=active_only,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def update(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        payload: ComplianceObligationUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        obligation = await self.get(company_id, obligation_id)
        if obligation.status in [ComplianceObligationStatus.COMPLETED, ComplianceObligationStatus.FULFILLED]:
            raise ValidationAppError(
                "Completed compliance obligations cannot be modified directly; reopen the obligation first",
                code="OBLIGATION_ALREADY_COMPLETED",
            )

        if payload.assigned_to is not None:
            await self._require_company_member(company_id, payload.assigned_to, "assigned_to")
        if payload.reviewer_id is not None:
            await self._require_company_member(company_id, payload.reviewer_id, "reviewer_id")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(obligation, field, value)

        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Compliance obligation {obligation.code} updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return obligation

    async def assign(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        *,
        assigned_to: uuid.UUID | None,
        reviewer_id: uuid.UUID | None,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        obligation = await self.get(company_id, obligation_id)
        if assigned_to is not None:
            await self._require_company_member(company_id, assigned_to, "assigned_to")
        if reviewer_id is not None:
            await self._require_company_member(company_id, reviewer_id, "reviewer_id")

        target_status = obligation.status
        action = "reassign" if obligation.assigned_to else "assign"
        if (obligation.status, action) in _OBLIGATION_TRANSITIONS:
            target_status = _OBLIGATION_TRANSITIONS[(obligation.status, action)]

        obligation.assigned_to = assigned_to
        obligation.reviewer_id = reviewer_id
        obligation.status = target_status

        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_ASSIGNED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Obligation {obligation.code} assigned to {assigned_to}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        if assigned_to:
            await self.notifications.create(
                company_id=company_id,
                user_id=assigned_to,
                type=NotificationType.OBLIGATION_ASSIGNED,
                title=f"Obligation Assigned: {obligation.name}",
                message=f"You have been assigned to obligation {obligation.code} (due {obligation.due_date})",
                severity=NotificationSeverity.INFO,
                entity_type="compliance_obligation",
                entity_id=obligation.id,
            )

        return obligation

    async def run_readiness(
        self, company_id: uuid.UUID, obligation_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> ReadinessResult:
        obligation = await self.get(company_id, obligation_id)
        result = await self.readiness.evaluate_obligation(company_id, obligation)

        obligation.readiness_status = result.overall_status.value
        obligation.readiness_details = result.to_dict()
        if result.overall_status == ReadinessStatus.BLOCKED and obligation.status not in [
            ComplianceObligationStatus.COMPLETED,
            ComplianceObligationStatus.FULFILLED,
        ]:
            obligation.status = ComplianceObligationStatus.BLOCKED
        elif obligation.status == ComplianceObligationStatus.BLOCKED and result.overall_status != ReadinessStatus.BLOCKED:
            obligation.status = ComplianceObligationStatus.ASSIGNED if obligation.assigned_to else ComplianceObligationStatus.IN_PROGRESS

        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_READINESS_CHECKED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Readiness check run for {obligation.code}: {result.overall_status.value}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return result

    async def submit_review(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        *,
        review_notes: str | None,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        obligation = await self.get(company_id, obligation_id)

        # Validate transition
        if (obligation.status, "submit_review") not in _OBLIGATION_TRANSITIONS:
            raise ConflictError(
                f"Cannot submit for review from status {obligation.status.value}",
                code="INVALID_OBLIGATION_STATUS_TRANSITION",
            )

        # Run readiness check and refuse if blocking prerequisites fail
        readiness_res = await self.readiness.evaluate_obligation(company_id, obligation)
        obligation.readiness_status = readiness_res.overall_status.value
        obligation.readiness_details = readiness_res.to_dict()

        if readiness_res.overall_status == ReadinessStatus.BLOCKED:
            obligation.status = ComplianceObligationStatus.BLOCKED
            await self.db.flush()
            raise ValidationAppError(
                f"Cannot submit for review: obligation has {readiness_res.blocking_issues_count} blocking prerequisite failure(s)",
                code="OBLIGATION_PREREQUISITES_BLOCKED",
            )

        obligation.status = _OBLIGATION_TRANSITIONS[(obligation.status, "submit_review")]
        if review_notes:
            obligation.review_notes = review_notes

        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_SUBMITTED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Obligation {obligation.code} submitted for review",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        notify_user = obligation.reviewer_id or obligation.created_by
        if notify_user and notify_user != current_user.id:
            await self.notifications.create(
                company_id=company_id,
                user_id=notify_user,
                type=NotificationType.OBLIGATION_REVIEW,
                title=f"Review Requested: {obligation.name}",
                message=f"Compliance obligation {obligation.code} has been submitted for your review.",
                severity=NotificationSeverity.INFO,
                entity_type="compliance_obligation",
                entity_id=obligation.id,
            )

        return obligation

    async def approve(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        *,
        review_notes: str | None,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        obligation = await self.get(company_id, obligation_id)
        if (obligation.status, "approve") not in _OBLIGATION_TRANSITIONS:
            raise ConflictError(
                f"Cannot approve obligation from status {obligation.status.value}",
                code="INVALID_OBLIGATION_STATUS_TRANSITION",
            )

        obligation.status = _OBLIGATION_TRANSITIONS[(obligation.status, "approve")]
        obligation.approved_at = datetime.now(timezone.utc)
        if review_notes:
            obligation.review_notes = review_notes

        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_APPROVED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Obligation {obligation.code} approved",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        if obligation.assigned_to and obligation.assigned_to != current_user.id:
            await self.notifications.create(
                company_id=company_id,
                user_id=obligation.assigned_to,
                type=NotificationType.OBLIGATION_APPROVED,
                title=f"Obligation Approved: {obligation.name}",
                message=f"Compliance obligation {obligation.code} was approved by reviewer.",
                severity=NotificationSeverity.INFO,
                entity_type="compliance_obligation",
                entity_id=obligation.id,
            )

        return obligation

    async def reject(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        *,
        review_notes: str | None,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        obligation = await self.get(company_id, obligation_id)
        if (obligation.status, "reject") not in _OBLIGATION_TRANSITIONS:
            raise ConflictError(
                f"Cannot reject obligation from status {obligation.status.value}",
                code="INVALID_OBLIGATION_STATUS_TRANSITION",
            )

        obligation.status = _OBLIGATION_TRANSITIONS[(obligation.status, "reject")]
        if review_notes:
            obligation.review_notes = review_notes

        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_REJECTED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Obligation {obligation.code} returned for changes: {review_notes}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        if obligation.assigned_to and obligation.assigned_to != current_user.id:
            await self.notifications.create(
                company_id=company_id,
                user_id=obligation.assigned_to,
                type=NotificationType.OBLIGATION_REJECTED,
                title=f"Obligation Returned: {obligation.name}",
                message=f"Compliance obligation {obligation.code} returned for changes. Note: {review_notes or 'No notes'}",
                severity=NotificationSeverity.WARNING,
                entity_type="compliance_obligation",
                entity_id=obligation.id,
            )

        return obligation

    async def complete(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        *,
        completion_notes: str | None,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        obligation = await self.get(company_id, obligation_id)
        if (obligation.status, "complete") not in _OBLIGATION_TRANSITIONS:
            raise ConflictError(
                f"Cannot complete obligation from status {obligation.status.value}",
                code="INVALID_OBLIGATION_STATUS_TRANSITION",
            )

        # Check readiness before completion
        readiness_res = await self.readiness.evaluate_obligation(company_id, obligation)
        obligation.readiness_status = readiness_res.overall_status.value
        obligation.readiness_details = readiness_res.to_dict()

        if readiness_res.overall_status == ReadinessStatus.BLOCKED:
            obligation.status = ComplianceObligationStatus.BLOCKED
            await self.db.flush()
            raise ValidationAppError(
                f"Cannot complete obligation: {readiness_res.blocking_issues_count} blocking prerequisite failure(s) unresolved",
                code="OBLIGATION_PREREQUISITES_BLOCKED",
            )

        obligation.status = _OBLIGATION_TRANSITIONS[(obligation.status, "complete")]
        obligation.completed_at = datetime.now(timezone.utc)
        if completion_notes:
            obligation.review_notes = completion_notes

        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_COMPLETED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Obligation {obligation.code} completed and signed off",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        if obligation.assigned_to and obligation.assigned_to != current_user.id:
            await self.notifications.create(
                company_id=company_id,
                user_id=obligation.assigned_to,
                type=NotificationType.OBLIGATION_COMPLETED,
                title=f"Obligation Completed: {obligation.name}",
                message=f"Compliance obligation {obligation.code} has been marked complete.",
                severity=NotificationSeverity.INFO,
                entity_type="compliance_obligation",
                entity_id=obligation.id,
            )

        return obligation

    async def reopen(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        *,
        reason: str,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        obligation = await self.get(company_id, obligation_id)
        if (obligation.status, "reopen") not in _OBLIGATION_TRANSITIONS:
            raise ConflictError(
                f"Cannot reopen obligation from status {obligation.status.value}",
                code="INVALID_OBLIGATION_STATUS_TRANSITION",
            )

        obligation.status = _OBLIGATION_TRANSITIONS[(obligation.status, "reopen")]
        obligation.review_notes = f"Reopened by {current_user.email}: {reason}"

        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_REOPENED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Obligation {obligation.code} reopened: {reason}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return obligation

    async def cancel(
        self, company_id: uuid.UUID, obligation_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> ComplianceObligation:
        obligation = await self.get(company_id, obligation_id)
        if (obligation.status, "cancel") not in _OBLIGATION_TRANSITIONS:
            raise ConflictError(
                f"Cannot cancel obligation from status {obligation.status.value}",
                code="INVALID_OBLIGATION_STATUS_TRANSITION",
            )

        obligation.status = _OBLIGATION_TRANSITIONS[(obligation.status, "cancel")]
        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_CANCELLED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Obligation {obligation.code} cancelled",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return obligation

    async def attach_evidence(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        *,
        document_id: uuid.UUID,
        description: str | None,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligationEvidence:
        obligation = await self.get(company_id, obligation_id)
        doc = await self.documents.get_by_id_for_company(document_id, company_id)
        if doc is None:
            raise NotFoundError("Document not found for this company", code="DOCUMENT_NOT_FOUND")

        evidence = ComplianceObligationEvidence(
            obligation_id=obligation.id,
            company_id=company_id,
            document_id=doc.id,
            description=description,
            created_by=current_user.id,
            created_at=datetime.now(timezone.utc),
        )
        await self.evidence_repo.create(evidence)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_EVIDENCE_ATTACHED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation_evidence",
            resource_id=str(evidence.id),
            description=f"Document {doc.original_filename} attached to obligation {obligation.code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return evidence

    async def list_evidence(
        self, company_id: uuid.UUID, obligation_id: uuid.UUID
    ) -> list[ComplianceObligationEvidence]:
        await self.get(company_id, obligation_id)
        return await self.evidence_repo.list_for_obligation(obligation_id, company_id)

    async def remove_evidence(
        self, company_id: uuid.UUID, obligation_id: uuid.UUID, evidence_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> None:
        await self.get(company_id, obligation_id)
        evidence = await self.evidence_repo.get_by_id(evidence_id, company_id)
        if evidence is None:
            raise NotFoundError("Evidence record not found", code="EVIDENCE_NOT_FOUND")

        await self.evidence_repo.delete(evidence)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_EVIDENCE_REMOVED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation_evidence",
            resource_id=str(evidence.id),
            description="Evidence removed from obligation",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

    async def sweep_overdue(self, company_id: uuid.UUID, current_user: User | None = None) -> int:
        today = date.today()
        candidates = await self.repo.list_open_past_due(company_id, as_of=today)
        overdue_count = 0

        for ob in candidates:
            if ob.status != ComplianceObligationStatus.OVERDUE:
                ob.status = ComplianceObligationStatus.OVERDUE
                overdue_count += 1

                user_id = current_user.id if current_user else ob.created_by
                await self.audit.log(
                    action=AuditAction.COMPLIANCE_OBLIGATION_UPDATED,
                    user_id=user_id,
                    company_id=company_id,
                    resource_type="compliance_obligation",
                    resource_id=str(ob.id),
                    description=f"Obligation {ob.code} automatically marked OVERDUE",
                    ip_address="127.0.0.1",
                    user_agent="compliance-scheduler",
                )

                if ob.assigned_to:
                    await self.notifications.create(
                        company_id=company_id,
                        user_id=ob.assigned_to,
                        type=NotificationType.OBLIGATION_OVERDUE,
                        title=f"OVERDUE: {ob.name}",
                        message=f"Compliance obligation {ob.code} is overdue (was due {ob.due_date})",
                        severity=NotificationSeverity.CRITICAL,
                        entity_type="compliance_obligation",
                        entity_id=ob.id,
                    )

        if overdue_count > 0:
            await self.db.flush()
        return overdue_count

    async def generate_task(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        payload: GenerateTaskRequest,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceTask:
        obligation = await self.get(company_id, obligation_id)
        if obligation.status in [ComplianceObligationStatus.COMPLETED, ComplianceObligationStatus.FULFILLED]:
            raise ValidationAppError(
                "Cannot generate a task from a completed obligation", code="COMPLIANCE_OBLIGATION_NOT_ACTIVE"
            )

        task = ComplianceTask(
            company_id=company_id,
            obligation_id=obligation.id,
            title=payload.title or obligation.name,
            description=obligation.description,
            category=obligation.category,
            module=obligation.module,
            priority=obligation.priority,
            assigned_to=payload.assigned_to or obligation.assigned_to,
            reviewer_id=payload.reviewer_id or obligation.reviewer_id,
            due_date=obligation.due_date,
            created_by=current_user.id,
        )
        await self.tasks.create(task)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_TASK_GENERATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_task",
            resource_id=str(task.id),
            description=f"Task generated from obligation {obligation.code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return task
