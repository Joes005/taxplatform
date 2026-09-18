"""Audit finding lifecycle: creation (with a duplicate-open-finding
warning, never a hard block, per PHASE7 §42), assignment, comments,
evidence (linking existing Phase 2 documents, never a second file store),
formal responses, and resolution. Severity/category here are internal
workflow classifications only — nothing in this service ever writes a
"FRAUD" or "ILLEGAL" label; the vocabulary is deliberately limited to
neutral review states (PHASE7 §18, §55).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.audit_finding import AuditFinding
from app.models.audit_finding_comment import AuditFindingComment
from app.models.audit_finding_evidence import AuditFindingEvidence
from app.models.audit_finding_response import AuditFindingResponse
from app.models.audit_workflow_enums import AuditFindingResponseStatus, AuditFindingStatus
from app.models.user import User
from app.repositories.audit_engagement_repository import AuditEngagementRepository
from app.repositories.audit_finding_evidence_repository import (
    AuditFindingCommentRepository,
    AuditFindingEvidenceRepository,
    AuditFindingResponseRepository,
)
from app.repositories.audit_finding_repository import AuditFindingRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.audit_finding import AuditFindingCreate, AuditFindingUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

_TRANSITIONS: dict[tuple[AuditFindingStatus, str], AuditFindingStatus] = {
    (AuditFindingStatus.OPEN, "assign"): AuditFindingStatus.ASSIGNED,
    (AuditFindingStatus.REOPENED, "assign"): AuditFindingStatus.ASSIGNED,
    (AuditFindingStatus.ACTION_REQUIRED, "assign"): AuditFindingStatus.ASSIGNED,
    (AuditFindingStatus.ASSIGNED, "start_review"): AuditFindingStatus.IN_REVIEW,
    (AuditFindingStatus.IN_REVIEW, "request_action"): AuditFindingStatus.ACTION_REQUIRED,
    (AuditFindingStatus.ASSIGNED, "submit_response"): AuditFindingStatus.RESPONSE_SUBMITTED,
    (AuditFindingStatus.ACTION_REQUIRED, "submit_response"): AuditFindingStatus.RESPONSE_SUBMITTED,
    (AuditFindingStatus.RESPONSE_SUBMITTED, "accept_response"): AuditFindingStatus.RESOLVED,
    (AuditFindingStatus.RESPONSE_SUBMITTED, "reject_response"): AuditFindingStatus.ACTION_REQUIRED,
    (AuditFindingStatus.OPEN, "resolve"): AuditFindingStatus.RESOLVED,
    (AuditFindingStatus.ASSIGNED, "resolve"): AuditFindingStatus.RESOLVED,
    (AuditFindingStatus.IN_REVIEW, "resolve"): AuditFindingStatus.RESOLVED,
    (AuditFindingStatus.ACTION_REQUIRED, "resolve"): AuditFindingStatus.RESOLVED,
    (AuditFindingStatus.RESPONSE_SUBMITTED, "resolve"): AuditFindingStatus.RESOLVED,
    (AuditFindingStatus.RESOLVED, "close"): AuditFindingStatus.CLOSED,
    (AuditFindingStatus.RESOLVED, "reopen"): AuditFindingStatus.REOPENED,
    (AuditFindingStatus.CLOSED, "reopen"): AuditFindingStatus.REOPENED,
    (AuditFindingStatus.REJECTED, "reopen"): AuditFindingStatus.REOPENED,
    (AuditFindingStatus.OPEN, "reject"): AuditFindingStatus.REJECTED,
    (AuditFindingStatus.ASSIGNED, "reject"): AuditFindingStatus.REJECTED,
    (AuditFindingStatus.IN_REVIEW, "reject"): AuditFindingStatus.REJECTED,
    (AuditFindingStatus.ACTION_REQUIRED, "reject"): AuditFindingStatus.REJECTED,
}


class AuditFindingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditFindingRepository(db)
        self.engagements = AuditEngagementRepository(db)
        self.evidence_repo = AuditFindingEvidenceRepository(db)
        self.comment_repo = AuditFindingCommentRepository(db)
        self.response_repo = AuditFindingResponseRepository(db)
        self.documents = DocumentRepository(db)
        self.audit = AuditService(db)

    async def create(
        self,
        company_id: uuid.UUID,
        engagement_id: uuid.UUID,
        payload: AuditFindingCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> tuple[AuditFinding, list[str]]:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")
        if engagement.is_locked:
            raise ConflictError("This engagement is locked", code="AUDIT_ENGAGEMENT_LOCKED")

        duplicates = await self.repo.find_potential_duplicates(
            engagement_id, source_type=payload.source_type, source_id=payload.source_id
        )

        finding_code = await self.repo.next_finding_code(engagement_id)
        finding = AuditFinding(
            engagement_id=engagement_id,
            company_id=company_id,
            finding_code=finding_code,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            severity=payload.severity,
            status=AuditFindingStatus.OPEN,
            source_type=payload.source_type,
            source_id=payload.source_id,
            assigned_to=payload.assigned_to,
            created_by=current_user.id,
            due_date=payload.due_date,
        )
        await self.repo.create(finding)

        if payload.assigned_to is not None:
            finding.status = AuditFindingStatus.ASSIGNED
            await self.db.flush()
            await self.db.refresh(finding)

        await self.audit.log(
            action=AuditAction.AUDIT_FINDING_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_finding",
            resource_id=str(finding.id),
            description=f"Finding {finding.finding_code} created: {finding.title}",
            metadata={"duplicate_of": [d.finding_code for d in duplicates]} if duplicates else None,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return finding, [d.finding_code for d in duplicates]

    async def get(self, company_id: uuid.UUID, finding_id: uuid.UUID) -> AuditFinding:
        finding = await self.repo.get_by_id_for_company(finding_id, company_id)
        if finding is None:
            raise NotFoundError("Audit finding not found", code="AUDIT_FINDING_NOT_FOUND")
        return finding

    async def list_for_engagement(self, company_id: uuid.UUID, engagement_id: uuid.UUID, **filters):
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")
        return await self.repo.list_for_engagement(engagement_id, **filters)

    async def list_for_company(self, company_id: uuid.UUID, **filters):
        return await self.repo.list_for_company(company_id, **filters)

    async def update(
        self,
        company_id: uuid.UUID,
        finding_id: uuid.UUID,
        payload: AuditFindingUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> AuditFinding:
        finding = await self.get(company_id, finding_id)

        if payload.title is not None:
            finding.title = payload.title
        if payload.description is not None:
            finding.description = payload.description
        if payload.category is not None:
            finding.category = payload.category
        if payload.severity is not None:
            finding.severity = payload.severity
        if payload.due_date is not None:
            finding.due_date = payload.due_date

        await self.db.flush()
        await self.db.refresh(finding)

        await self.audit.log(
            action=AuditAction.AUDIT_FINDING_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_finding",
            resource_id=str(finding.id),
            description=f"Finding {finding.finding_code} updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return finding

    async def _transition(
        self,
        company_id: uuid.UUID,
        finding_id: uuid.UUID,
        action: str,
        current_user: User,
        meta: RequestMeta,
        *,
        audit_action: str,
        extra_description: str | None = None,
    ) -> AuditFinding:
        finding = await self.get(company_id, finding_id)
        key = (finding.status, action)
        if key not in _TRANSITIONS:
            raise ConflictError(
                f"Cannot {action.replace('_', ' ')} a finding in status {finding.status.value}",
                code="INVALID_AUDIT_FINDING_TRANSITION",
            )
        finding.status = _TRANSITIONS[key]
        await self.db.flush()
        await self.db.refresh(finding)

        await self.audit.log(
            action=audit_action,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_finding",
            resource_id=str(finding.id),
            description=extra_description or f"Finding {finding.finding_code} moved to {finding.status.value}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return finding

    async def assign(
        self, company_id: uuid.UUID, finding_id: uuid.UUID, assigned_to: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> AuditFinding:
        finding = await self.get(company_id, finding_id)
        finding.assigned_to = assigned_to
        await self.db.flush()
        return await self._transition(
            company_id,
            finding_id,
            "assign",
            current_user,
            meta,
            audit_action=AuditAction.AUDIT_FINDING_ASSIGNED,
            extra_description=f"Finding {finding.finding_code} assigned",
        )

    async def start_review(self, company_id, finding_id, current_user, meta) -> AuditFinding:
        return await self._transition(
            company_id, finding_id, "start_review", current_user, meta,
            audit_action=AuditAction.AUDIT_FINDING_STATUS_CHANGED,
        )

    async def request_action(self, company_id, finding_id, current_user, meta) -> AuditFinding:
        return await self._transition(
            company_id, finding_id, "request_action", current_user, meta,
            audit_action=AuditAction.AUDIT_FINDING_STATUS_CHANGED,
        )

    async def resolve(
        self, company_id: uuid.UUID, finding_id: uuid.UUID, resolution_summary: str, current_user: User, meta: RequestMeta
    ) -> AuditFinding:
        finding = await self._transition(
            company_id, finding_id, "resolve", current_user, meta,
            audit_action=AuditAction.AUDIT_FINDING_STATUS_CHANGED,
        )
        finding.resolution_summary = resolution_summary
        finding.resolved_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(finding)
        return finding

    async def close(self, company_id, finding_id, current_user, meta) -> AuditFinding:
        finding = await self._transition(
            company_id, finding_id, "close", current_user, meta,
            audit_action=AuditAction.AUDIT_FINDING_STATUS_CHANGED,
        )
        finding.closed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(finding)
        return finding

    async def reopen(
        self, company_id: uuid.UUID, finding_id: uuid.UUID, reason: str, current_user: User, meta: RequestMeta
    ) -> AuditFinding:
        finding = await self._transition(
            company_id, finding_id, "reopen", current_user, meta,
            audit_action=AuditAction.AUDIT_FINDING_STATUS_CHANGED,
            extra_description=f"Finding reopened: {reason}",
        )
        finding.resolution_summary = None
        finding.resolved_at = None
        finding.closed_at = None
        await self.db.flush()
        await self.db.refresh(finding)
        return finding

    async def reject(
        self, company_id: uuid.UUID, finding_id: uuid.UUID, reason: str, current_user: User, meta: RequestMeta
    ) -> AuditFinding:
        return await self._transition(
            company_id, finding_id, "reject", current_user, meta,
            audit_action=AuditAction.AUDIT_FINDING_STATUS_CHANGED,
            extra_description=f"Finding rejected: {reason}",
        )

    async def add_comment(
        self, company_id: uuid.UUID, finding_id: uuid.UUID, comment_text: str, current_user: User, meta: RequestMeta
    ) -> AuditFindingComment:
        finding = await self.get(company_id, finding_id)
        comment = AuditFindingComment(
            finding_id=finding.id,
            company_id=company_id,
            user_id=current_user.id,
            comment=comment_text,
            created_at=datetime.now(timezone.utc),
        )
        await self.comment_repo.create(comment)

        await self.audit.log(
            action=AuditAction.AUDIT_FINDING_COMMENT_ADDED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_finding",
            resource_id=str(finding.id),
            description=f"Comment added on finding {finding.finding_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return comment

    async def list_comments(self, company_id: uuid.UUID, finding_id: uuid.UUID) -> list[AuditFindingComment]:
        finding = await self.get(company_id, finding_id)
        return await self.comment_repo.list_for_finding(finding.id)

    async def add_evidence(
        self,
        company_id: uuid.UUID,
        finding_id: uuid.UUID,
        document_id: uuid.UUID,
        description: str | None,
        current_user: User,
        meta: RequestMeta,
    ) -> AuditFindingEvidence:
        finding = await self.get(company_id, finding_id)
        document = await self.documents.get_by_id_for_company(document_id, company_id)
        if document is None:
            raise ValidationAppError("Document not found for this company", code="DOCUMENT_NOT_FOUND")

        evidence = AuditFindingEvidence(
            finding_id=finding.id,
            company_id=company_id,
            document_id=document_id,
            description=description,
            added_by=current_user.id,
            added_at=datetime.now(timezone.utc),
        )
        await self.evidence_repo.create(evidence)

        await self.audit.log(
            action=AuditAction.AUDIT_FINDING_EVIDENCE_ADDED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_finding",
            resource_id=str(finding.id),
            description=f"Evidence attached to finding {finding.finding_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return evidence

    async def remove_evidence(
        self, company_id: uuid.UUID, finding_id: uuid.UUID, evidence_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> None:
        finding = await self.get(company_id, finding_id)
        evidence = await self.evidence_repo.get_by_id_for_company(evidence_id, company_id)
        if evidence is None or evidence.finding_id != finding.id:
            raise NotFoundError("Evidence not found", code="AUDIT_FINDING_EVIDENCE_NOT_FOUND")

        await self.evidence_repo.delete(evidence)

        await self.audit.log(
            action=AuditAction.AUDIT_FINDING_EVIDENCE_REMOVED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_finding",
            resource_id=str(finding.id),
            description=f"Evidence removed from finding {finding.finding_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

    async def list_evidence(self, company_id: uuid.UUID, finding_id: uuid.UUID) -> list[AuditFindingEvidence]:
        finding = await self.get(company_id, finding_id)
        return await self.evidence_repo.list_for_finding(finding.id)

    async def submit_response(
        self, company_id: uuid.UUID, finding_id: uuid.UUID, response_text: str, current_user: User, meta: RequestMeta
    ) -> AuditFindingResponse:
        finding = await self.get(company_id, finding_id)
        key = (finding.status, "submit_response")
        if key not in _TRANSITIONS:
            raise ConflictError(
                f"Cannot submit a response while finding is in status {finding.status.value}",
                code="INVALID_AUDIT_FINDING_TRANSITION",
            )

        response = AuditFindingResponse(
            finding_id=finding.id,
            company_id=company_id,
            submitted_by=current_user.id,
            response_text=response_text,
            submitted_at=datetime.now(timezone.utc),
            status=AuditFindingResponseStatus.SUBMITTED,
        )
        await self.response_repo.create(response)

        finding.status = _TRANSITIONS[key]
        await self.db.flush()
        await self.db.refresh(finding)

        await self.audit.log(
            action=AuditAction.AUDIT_FINDING_RESPONSE_SUBMITTED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_finding",
            resource_id=str(finding.id),
            description=f"Response submitted for finding {finding.finding_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return response

    async def review_response(
        self,
        company_id: uuid.UUID,
        finding_id: uuid.UUID,
        response_id: uuid.UUID,
        accept: bool,
        review_comment: str | None,
        current_user: User,
        meta: RequestMeta,
    ) -> AuditFindingResponse:
        finding = await self.get(company_id, finding_id)
        response = await self.response_repo.get_by_id_for_company(response_id, company_id)
        if response is None or response.finding_id != finding.id:
            raise NotFoundError("Response not found", code="AUDIT_FINDING_RESPONSE_NOT_FOUND")
        if response.status != AuditFindingResponseStatus.SUBMITTED:
            raise ConflictError("This response has already been reviewed", code="AUDIT_FINDING_RESPONSE_ALREADY_REVIEWED")

        response.status = (
            AuditFindingResponseStatus.ACCEPTED if accept else AuditFindingResponseStatus.REJECTED
        )
        response.reviewed_by = current_user.id
        response.reviewed_at = datetime.now(timezone.utc)
        response.review_comment = review_comment
        await self.db.flush()

        action = "accept_response" if accept else "reject_response"
        key = (finding.status, action)
        if key in _TRANSITIONS:
            finding.status = _TRANSITIONS[key]
            if accept:
                finding.resolution_summary = response.response_text
                finding.resolved_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(finding)

        await self.audit.log(
            action=AuditAction.AUDIT_FINDING_RESPONSE_REVIEWED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_finding",
            resource_id=str(finding.id),
            description=f"Response {'accepted' if accept else 'rejected'} for finding {finding.finding_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return response

    async def list_responses(self, company_id: uuid.UUID, finding_id: uuid.UUID) -> list[AuditFindingResponse]:
        finding = await self.get(company_id, finding_id)
        return await self.response_repo.list_for_finding(finding.id)
