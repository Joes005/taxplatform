"""Engagement staffing (PHASE7 §10-11). A user can only be assigned to an
engagement while holding an active `CompanyMembership` for that
engagement's company — this service never creates a new kind of user or
grants access outside the existing RBAC/membership system. Unassigning
sets `is_active=False` rather than deleting, preserving who was on the
engagement and when.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.audit_assignment import AuditAssignment
from app.models.audit_workflow_enums import AuditEngagementStatus
from app.models.user import User
from app.repositories.audit_assignment_repository import AuditAssignmentRepository
from app.repositories.audit_engagement_repository import AuditEngagementRepository
from app.repositories.membership_repository import MembershipRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class AuditAssignmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditAssignmentRepository(db)
        self.engagements = AuditEngagementRepository(db)
        self.memberships = MembershipRepository(db)
        self.audit = AuditService(db)

    async def assign(
        self,
        company_id: uuid.UUID,
        engagement_id: uuid.UUID,
        user_id: uuid.UUID,
        role,
        current_user: User,
        meta: RequestMeta,
    ) -> AuditAssignment:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")
        if engagement.is_locked:
            raise ConflictError("This engagement is locked", code="AUDIT_ENGAGEMENT_LOCKED")

        membership = await self.memberships.get_active_membership(user_id=user_id, company_id=company_id)
        if membership is None:
            raise ValidationAppError(
                "This user does not have active access to this company", code="USER_NOT_A_COMPANY_MEMBER"
            )

        existing = await self.repo.get_active(engagement_id, user_id, role)
        if existing is not None:
            raise ConflictError(
                "This user already holds this role on this engagement", code="AUDIT_ASSIGNMENT_ALREADY_ACTIVE"
            )

        assignment = AuditAssignment(
            engagement_id=engagement_id,
            company_id=company_id,
            user_id=user_id,
            role=role,
            assigned_by=current_user.id,
            assigned_at=datetime.now(timezone.utc),
        )
        await self.repo.create(assignment)

        if engagement.status == AuditEngagementStatus.OPEN:
            engagement.status = AuditEngagementStatus.ASSIGNED
            await self.db.flush()

        await self.audit.log(
            action=AuditAction.AUDIT_ASSIGNMENT_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_assignment",
            resource_id=str(assignment.id),
            description=f"User assigned as {role.value} to engagement {engagement.engagement_code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return assignment

    async def unassign(
        self,
        company_id: uuid.UUID,
        engagement_id: uuid.UUID,
        assignment_id: uuid.UUID,
        current_user: User,
        meta: RequestMeta,
    ) -> AuditAssignment:
        assignment = await self.repo.get_by_id_for_company(assignment_id, company_id)
        if assignment is None or assignment.engagement_id != engagement_id:
            raise NotFoundError("Audit assignment not found", code="AUDIT_ASSIGNMENT_NOT_FOUND")
        if not assignment.is_active:
            raise ConflictError("This assignment is already inactive", code="AUDIT_ASSIGNMENT_NOT_ACTIVE")

        assignment.is_active = False
        assignment.unassigned_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(assignment)

        await self.audit.log(
            action=AuditAction.AUDIT_ASSIGNMENT_REMOVED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_assignment",
            resource_id=str(assignment.id),
            description=f"Assignment removed from engagement {engagement_id}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return assignment

    async def list_for_engagement(self, company_id: uuid.UUID, engagement_id: uuid.UUID) -> list[AuditAssignment]:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")
        return await self.repo.list_for_engagement(engagement_id)
