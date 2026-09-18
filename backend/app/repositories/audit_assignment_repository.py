import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_assignment import AuditAssignment
from app.models.audit_workflow_enums import AuditAssignmentRole


class AuditAssignmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, assignment: AuditAssignment) -> AuditAssignment:
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def get_by_id_for_company(
        self, assignment_id: uuid.UUID, company_id: uuid.UUID
    ) -> AuditAssignment | None:
        result = await self.db.execute(
            select(AuditAssignment).where(
                AuditAssignment.id == assignment_id, AuditAssignment.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_active(
        self, engagement_id: uuid.UUID, user_id: uuid.UUID, role: AuditAssignmentRole
    ) -> AuditAssignment | None:
        result = await self.db.execute(
            select(AuditAssignment).where(
                AuditAssignment.engagement_id == engagement_id,
                AuditAssignment.user_id == user_id,
                AuditAssignment.role == role,
                AuditAssignment.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_engagement(
        self, engagement_id: uuid.UUID, *, active_only: bool = True
    ) -> list[AuditAssignment]:
        query = select(AuditAssignment).where(AuditAssignment.engagement_id == engagement_id)
        if active_only:
            query = query.where(AuditAssignment.is_active.is_(True))
        result = await self.db.execute(query.order_by(AuditAssignment.assigned_at.asc()))
        return list(result.scalars().all())

    async def count_active_by_role(self, engagement_id: uuid.UUID, role: AuditAssignmentRole) -> int:
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count())
            .select_from(AuditAssignment)
            .where(
                AuditAssignment.engagement_id == engagement_id,
                AuditAssignment.role == role,
                AuditAssignment.is_active.is_(True),
            )
        )
        return result.scalar_one()
