"""Review passes and sign-off (PHASE7 §25, §28-29). A review is a
free-form summary/notes record a reviewer files against an engagement —
it never itself changes the engagement's status; the engagement's own
lifecycle (submit/approve/return) stays the single source of truth for
"where is this engagement in its workflow." A sign-off is always the
platform's fixed, neutral acknowledgement text — never freely authored —
so the system can never be made to emit a "legally certified" claim.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.audit_review import AuditReview
from app.models.audit_signoff import AuditSignOff
from app.models.audit_workflow_enums import (
    AuditEngagementStatus,
    AuditReviewStatus,
    AuditReviewType,
    AuditSignOffType,
)
from app.models.user import User
from app.repositories.audit_engagement_repository import AuditEngagementRepository
from app.repositories.audit_review_repository import AuditReviewRepository, AuditSignOffRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

_SIGNOFF_STATEMENTS = {
    AuditSignOffType.LEAD_AUDITOR: (
        "This engagement's review has been completed by the assigned lead auditor within this "
        "platform. This is an internal workflow acknowledgement only and does not constitute a "
        "statutory audit opinion, certification, or digitally signed filing."
    ),
    AuditSignOffType.REVIEWER: (
        "This engagement has undergone reviewer sign-off within this platform's internal workflow. "
        "This is an internal acknowledgement only and does not constitute a statutory certification."
    ),
    AuditSignOffType.COMPANY_ACKNOWLEDGEMENT: (
        "The company acknowledges that this engagement's findings and checklist have been reviewed "
        "within this platform. This is an internal acknowledgement only and carries no statutory or "
        "legal effect."
    ),
}


class AuditReviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditReviewRepository(db)
        self.engagements = AuditEngagementRepository(db)
        self.audit = AuditService(db)

    async def start(
        self, company_id: uuid.UUID, engagement_id: uuid.UUID, review_type: AuditReviewType, current_user: User, meta: RequestMeta
    ) -> AuditReview:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")

        review = AuditReview(
            engagement_id=engagement_id,
            company_id=company_id,
            reviewer_id=current_user.id,
            review_type=review_type,
            status=AuditReviewStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
        )
        await self.repo.create(review)

        await self.audit.log(
            action=AuditAction.AUDIT_REVIEW_STARTED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_review",
            resource_id=str(review.id),
            description=f"{review_type.value} started for engagement {engagement.engagement_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return review

    async def get(self, company_id: uuid.UUID, review_id: uuid.UUID) -> AuditReview:
        review = await self.repo.get_by_id_for_company(review_id, company_id)
        if review is None:
            raise NotFoundError("Audit review not found", code="AUDIT_REVIEW_NOT_FOUND")
        return review

    async def list_for_engagement(self, company_id: uuid.UUID, engagement_id: uuid.UUID) -> list[AuditReview]:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")
        return await self.repo.list_for_engagement(engagement_id)

    async def complete(
        self, company_id: uuid.UUID, review_id: uuid.UUID, summary: str | None, notes: str | None, current_user: User, meta: RequestMeta
    ) -> AuditReview:
        review = await self.get(company_id, review_id)
        if review.status != AuditReviewStatus.IN_PROGRESS:
            raise ConflictError("Only an in-progress review can be completed", code="AUDIT_REVIEW_NOT_IN_PROGRESS")

        review.status = AuditReviewStatus.COMPLETED
        review.summary = summary
        review.notes = notes
        review.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(review)

        await self.audit.log(
            action=AuditAction.AUDIT_REVIEW_COMPLETED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_review",
            resource_id=str(review.id),
            description="Review completed",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return review

    async def return_review(
        self, company_id: uuid.UUID, review_id: uuid.UUID, notes: str, current_user: User, meta: RequestMeta
    ) -> AuditReview:
        review = await self.get(company_id, review_id)
        if review.status != AuditReviewStatus.IN_PROGRESS:
            raise ConflictError("Only an in-progress review can be returned", code="AUDIT_REVIEW_NOT_IN_PROGRESS")

        review.status = AuditReviewStatus.RETURNED
        review.notes = notes
        await self.db.flush()
        await self.db.refresh(review)

        await self.audit.log(
            action=AuditAction.AUDIT_REVIEW_RETURNED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_review",
            resource_id=str(review.id),
            description=f"Review returned: {notes}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return review


class AuditSignOffService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditSignOffRepository(db)
        self.engagements = AuditEngagementRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, engagement_id: uuid.UUID, sign_off_type: AuditSignOffType, current_user: User, meta: RequestMeta
    ) -> AuditSignOff:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")
        if engagement.status != AuditEngagementStatus.APPROVED:
            raise ConflictError(
                "Sign-off can only be recorded once an engagement is APPROVED",
                code="AUDIT_ENGAGEMENT_NOT_APPROVED",
            )

        signoff = AuditSignOff(
            engagement_id=engagement_id,
            company_id=company_id,
            signed_by=current_user.id,
            sign_off_type=sign_off_type,
            statement=_SIGNOFF_STATEMENTS[sign_off_type],
            created_at=datetime.now(timezone.utc),
        )
        await self.repo.create(signoff)

        await self.audit.log(
            action=AuditAction.AUDIT_SIGNOFF_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_signoff",
            resource_id=str(signoff.id),
            description=f"{sign_off_type.value} sign-off recorded for engagement {engagement.engagement_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return signoff

    async def list_for_engagement(self, company_id: uuid.UUID, engagement_id: uuid.UUID) -> list[AuditSignOff]:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")
        return await self.repo.list_for_engagement(engagement_id)
