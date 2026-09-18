"""CA/Auditor engagement lifecycle (PHASE7 §9, §26-27):

DRAFT -> OPEN -> ASSIGNED -> IN_REVIEW <-> PENDING_CLIENT_ACTION
       IN_REVIEW -> PENDING_AUDITOR_REVIEW -> APPROVED -> SIGNED_OFF -> CLOSED
       PENDING_AUDITOR_REVIEW -> IN_REVIEW (returned for changes)
       DRAFT/OPEN/ASSIGNED/IN_REVIEW/PENDING_CLIENT_ACTION -> CANCELLED

`is_locked` is a separate immutability switch reachable only once CLOSED —
it is not itself a lifecycle status. Approval is blocked while any
HIGH/CRITICAL finding is still open, or any checklist item still needs
attention, so nobody can rubber-stamp an engagement with known unresolved
issues (PHASE7 §26-27) — the engine flags and blocks, it never
auto-resolves anything on the CA's behalf.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.audit_engagement import AuditEngagement
from app.models.audit_workflow_enums import (
    AuditChecklistItemStatus,
    AuditEngagementStatus,
    AuditFindingSeverity,
    AuditFindingStatus,
)
from app.models.user import User
from app.repositories.audit_checklist_repository import AuditChecklistRepository
from app.repositories.audit_engagement_repository import AuditEngagementRepository
from app.repositories.audit_finding_repository import AuditFindingRepository
from app.repositories.audit_review_repository import AuditSignOffRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.schemas.audit_engagement import AuditEngagementCreate, AuditEngagementUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

_TRANSITIONS: dict[tuple[AuditEngagementStatus, str], AuditEngagementStatus] = {
    (AuditEngagementStatus.DRAFT, "open"): AuditEngagementStatus.OPEN,
    (AuditEngagementStatus.OPEN, "start_review"): AuditEngagementStatus.IN_REVIEW,
    (AuditEngagementStatus.ASSIGNED, "start_review"): AuditEngagementStatus.IN_REVIEW,
    (AuditEngagementStatus.IN_REVIEW, "request_client_action"): AuditEngagementStatus.PENDING_CLIENT_ACTION,
    (AuditEngagementStatus.PENDING_CLIENT_ACTION, "resume_review"): AuditEngagementStatus.IN_REVIEW,
    (AuditEngagementStatus.IN_REVIEW, "submit_for_review"): AuditEngagementStatus.PENDING_AUDITOR_REVIEW,
    (AuditEngagementStatus.PENDING_AUDITOR_REVIEW, "approve"): AuditEngagementStatus.APPROVED,
    (AuditEngagementStatus.PENDING_AUDITOR_REVIEW, "return_for_changes"): AuditEngagementStatus.IN_REVIEW,
    (AuditEngagementStatus.APPROVED, "sign_off"): AuditEngagementStatus.SIGNED_OFF,
    (AuditEngagementStatus.SIGNED_OFF, "close"): AuditEngagementStatus.CLOSED,
    (AuditEngagementStatus.DRAFT, "cancel"): AuditEngagementStatus.CANCELLED,
    (AuditEngagementStatus.OPEN, "cancel"): AuditEngagementStatus.CANCELLED,
    (AuditEngagementStatus.ASSIGNED, "cancel"): AuditEngagementStatus.CANCELLED,
    (AuditEngagementStatus.IN_REVIEW, "cancel"): AuditEngagementStatus.CANCELLED,
    (AuditEngagementStatus.PENDING_CLIENT_ACTION, "cancel"): AuditEngagementStatus.CANCELLED,
}

_AUDIT_ACTION_BY_ACTION = {
    "open": AuditAction.AUDIT_ENGAGEMENT_UPDATED,
    "start_review": AuditAction.AUDIT_ENGAGEMENT_UPDATED,
    "request_client_action": AuditAction.AUDIT_ENGAGEMENT_UPDATED,
    "resume_review": AuditAction.AUDIT_ENGAGEMENT_UPDATED,
    "submit_for_review": AuditAction.AUDIT_ENGAGEMENT_UPDATED,
    "approve": AuditAction.AUDIT_ENGAGEMENT_APPROVED,
    "return_for_changes": AuditAction.AUDIT_ENGAGEMENT_UPDATED,
    "sign_off": AuditAction.AUDIT_ENGAGEMENT_UPDATED,
    "close": AuditAction.AUDIT_ENGAGEMENT_CLOSED,
    "cancel": AuditAction.AUDIT_ENGAGEMENT_CANCELLED,
}

_BLOCKING_FINDING_STATUSES = {
    AuditFindingStatus.OPEN,
    AuditFindingStatus.ASSIGNED,
    AuditFindingStatus.IN_REVIEW,
    AuditFindingStatus.ACTION_REQUIRED,
    AuditFindingStatus.RESPONSE_SUBMITTED,
    AuditFindingStatus.REOPENED,
}


class AuditEngagementService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditEngagementRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.checklists = AuditChecklistRepository(db)
        self.findings = AuditFindingRepository(db)
        self.signoffs = AuditSignOffRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: AuditEngagementCreate, current_user: User, meta: RequestMeta
    ) -> AuditEngagement:
        financial_year = await self.financial_years.get_by_id_for_company(payload.financial_year_id, company_id)
        if financial_year is None:
            raise ValidationAppError("Financial year not found for this company", code="FINANCIAL_YEAR_NOT_FOUND")

        engagement_code = await self.repo.next_engagement_code(company_id)
        engagement = AuditEngagement(
            company_id=company_id,
            engagement_code=engagement_code,
            title=payload.title,
            description=payload.description,
            financial_year_id=financial_year.id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            engagement_type=payload.engagement_type,
            status=AuditEngagementStatus.DRAFT,
            created_by=current_user.id,
        )
        await self.repo.create(engagement)

        await self.audit.log(
            action=AuditAction.AUDIT_ENGAGEMENT_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_engagement",
            resource_id=str(engagement.id),
            description=f"Audit engagement {engagement.engagement_code} created: {engagement.title}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return engagement

    async def get(self, company_id: uuid.UUID, engagement_id: uuid.UUID) -> AuditEngagement:
        engagement = await self.repo.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")
        return engagement

    async def list(
        self,
        company_id: uuid.UUID,
        *,
        status: AuditEngagementStatus | None,
        financial_year_id: uuid.UUID | None,
        assigned_to: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AuditEngagement], int]:
        return await self.repo.list_for_company(
            company_id,
            status=status,
            financial_year_id=financial_year_id,
            assigned_to=assigned_to,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def update(
        self,
        company_id: uuid.UUID,
        engagement_id: uuid.UUID,
        payload: AuditEngagementUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> AuditEngagement:
        engagement = await self.get(company_id, engagement_id)
        if engagement.is_locked:
            raise ConflictError("This engagement is locked and cannot be edited", code="AUDIT_ENGAGEMENT_LOCKED")

        if payload.title is not None:
            engagement.title = payload.title
        if payload.description is not None:
            engagement.description = payload.description
        if payload.engagement_type is not None:
            engagement.engagement_type = payload.engagement_type

        await self.db.flush()
        await self.db.refresh(engagement)

        await self.audit.log(
            action=AuditAction.AUDIT_ENGAGEMENT_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_engagement",
            resource_id=str(engagement.id),
            description=f"Audit engagement {engagement.engagement_code} updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return engagement

    async def _check_can_approve(self, company_id: uuid.UUID, engagement: AuditEngagement) -> None:
        counts = await self.findings.count_by_status_for_engagement(engagement.id)
        open_high_or_critical = 0
        open_findings, _total = await self.findings.list_for_engagement(
            engagement.id, offset=0, limit=1000
        )
        for finding in open_findings:
            if finding.status in _BLOCKING_FINDING_STATUSES and finding.severity in (
                AuditFindingSeverity.HIGH,
                AuditFindingSeverity.CRITICAL,
            ):
                open_high_or_critical += 1
        if open_high_or_critical:
            raise ConflictError(
                f"Cannot approve: {open_high_or_critical} HIGH/CRITICAL finding(s) are still open",
                code="AUDIT_ENGAGEMENT_OPEN_FINDINGS_BLOCK_APPROVAL",
                details={"counts_by_status": {k.value: v for k, v in counts.items()}},
            )

        checklist = await self.checklists.get_for_engagement(engagement.id, company_id)
        if checklist is not None:
            needs_attention = [
                item for item in checklist.items if item.status == AuditChecklistItemStatus.REQUIRES_ATTENTION
            ]
            if needs_attention:
                raise ConflictError(
                    f"Cannot approve: {len(needs_attention)} checklist item(s) still require attention",
                    code="AUDIT_ENGAGEMENT_CHECKLIST_BLOCKS_APPROVAL",
                )

    async def _transition(
        self,
        company_id: uuid.UUID,
        engagement_id: uuid.UUID,
        action: str,
        current_user: User,
        meta: RequestMeta,
        comment: str | None = None,
    ) -> AuditEngagement:
        engagement = await self.get(company_id, engagement_id)
        if engagement.is_locked:
            raise ConflictError("This engagement is locked", code="AUDIT_ENGAGEMENT_LOCKED")

        key = (engagement.status, action)
        if key not in _TRANSITIONS:
            raise ConflictError(
                f"Cannot {action.replace('_', ' ')} an engagement in status {engagement.status.value}",
                code="INVALID_AUDIT_ENGAGEMENT_TRANSITION",
            )

        if action == "approve":
            await self._check_can_approve(company_id, engagement)

        if action == "sign_off":
            from app.models.audit_workflow_enums import AuditSignOffType

            signoffs = await self.signoffs.list_for_engagement(engagement.id)
            if not any(s.sign_off_type == AuditSignOffType.LEAD_AUDITOR for s in signoffs):
                raise ConflictError(
                    "A lead auditor sign-off must be recorded before this engagement can be marked signed off",
                    code="AUDIT_ENGAGEMENT_MISSING_LEAD_SIGNOFF",
                )

        engagement.status = _TRANSITIONS[key]

        if action == "close":
            engagement.status = AuditEngagementStatus.CLOSED

        await self.db.flush()
        await self.db.refresh(engagement)

        await self.audit.log(
            action=_AUDIT_ACTION_BY_ACTION[action],
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_engagement",
            resource_id=str(engagement.id),
            description=f"Audit engagement {engagement.engagement_code} moved to {engagement.status.value}",
            metadata={"comment": comment} if comment else None,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return engagement

    async def open(self, company_id, engagement_id, current_user, meta) -> AuditEngagement:
        return await self._transition(company_id, engagement_id, "open", current_user, meta)

    async def start_review(self, company_id, engagement_id, current_user, meta) -> AuditEngagement:
        return await self._transition(company_id, engagement_id, "start_review", current_user, meta)

    async def request_client_action(self, company_id, engagement_id, current_user, meta, comment=None) -> AuditEngagement:
        return await self._transition(
            company_id, engagement_id, "request_client_action", current_user, meta, comment
        )

    async def resume_review(self, company_id, engagement_id, current_user, meta) -> AuditEngagement:
        return await self._transition(company_id, engagement_id, "resume_review", current_user, meta)

    async def submit_for_review(self, company_id, engagement_id, current_user, meta) -> AuditEngagement:
        return await self._transition(company_id, engagement_id, "submit_for_review", current_user, meta)

    async def approve(self, company_id, engagement_id, current_user, meta, comment=None) -> AuditEngagement:
        return await self._transition(company_id, engagement_id, "approve", current_user, meta, comment)

    async def return_for_changes(self, company_id, engagement_id, current_user, meta, comment=None) -> AuditEngagement:
        return await self._transition(
            company_id, engagement_id, "return_for_changes", current_user, meta, comment
        )

    async def sign_off_transition(self, company_id, engagement_id, current_user, meta) -> AuditEngagement:
        return await self._transition(company_id, engagement_id, "sign_off", current_user, meta)

    async def close(self, company_id, engagement_id, current_user, meta) -> AuditEngagement:
        return await self._transition(company_id, engagement_id, "close", current_user, meta)

    async def cancel(self, company_id, engagement_id, current_user, meta, comment=None) -> AuditEngagement:
        return await self._transition(company_id, engagement_id, "cancel", current_user, meta, comment)

    async def lock(self, company_id: uuid.UUID, engagement_id: uuid.UUID, current_user: User, meta: RequestMeta) -> AuditEngagement:
        engagement = await self.get(company_id, engagement_id)
        if engagement.status != AuditEngagementStatus.CLOSED:
            raise ConflictError(
                "Only a closed engagement can be locked", code="AUDIT_ENGAGEMENT_NOT_CLOSED"
            )
        if engagement.is_locked:
            raise ConflictError("This engagement is already locked", code="AUDIT_ENGAGEMENT_ALREADY_LOCKED")

        engagement.is_locked = True
        engagement.locked_at = datetime.now(timezone.utc)
        engagement.locked_by = current_user.id
        await self.db.flush()
        await self.db.refresh(engagement)

        await self.audit.log(
            action=AuditAction.AUDIT_ENGAGEMENT_LOCKED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_engagement",
            resource_id=str(engagement.id),
            description=f"Audit engagement {engagement.engagement_code} locked",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return engagement
