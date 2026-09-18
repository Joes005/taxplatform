import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_engagement import AuditEngagement
from app.models.audit_workflow_enums import AuditEngagementStatus


class AuditEngagementRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, engagement: AuditEngagement) -> AuditEngagement:
        self.db.add(engagement)
        await self.db.flush()
        return engagement

    async def get_by_id_for_company(
        self, engagement_id: uuid.UUID, company_id: uuid.UUID
    ) -> AuditEngagement | None:
        result = await self.db.execute(
            select(AuditEngagement).where(
                AuditEngagement.id == engagement_id, AuditEngagement.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code_for_company(
        self, company_id: uuid.UUID, engagement_code: str
    ) -> AuditEngagement | None:
        result = await self.db.execute(
            select(AuditEngagement).where(
                AuditEngagement.company_id == company_id,
                AuditEngagement.engagement_code == engagement_code,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        status: AuditEngagementStatus | None = None,
        financial_year_id: uuid.UUID | None = None,
        assigned_to: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AuditEngagement], int]:
        query = select(AuditEngagement).where(AuditEngagement.company_id == company_id)
        if status is not None:
            query = query.where(AuditEngagement.status == status)
        if financial_year_id is not None:
            query = query.where(AuditEngagement.financial_year_id == financial_year_id)
        if assigned_to is not None:
            from app.models.audit_assignment import AuditAssignment

            query = query.where(
                AuditEngagement.id.in_(
                    select(AuditAssignment.engagement_id).where(
                        AuditAssignment.user_id == assigned_to,
                        AuditAssignment.is_active.is_(True),
                    )
                )
            )

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.order_by(AuditEngagement.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def next_engagement_code(self, company_id: uuid.UUID) -> str:
        count_result = await self.db.execute(
            select(func.count()).select_from(AuditEngagement).where(AuditEngagement.company_id == company_id)
        )
        count = count_result.scalar_one()
        return f"ENG-{count + 1:04d}"
