import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_finding import AuditFinding
from app.models.audit_workflow_enums import (
    AuditFindingCategory,
    AuditFindingSeverity,
    AuditFindingSourceType,
    AuditFindingStatus,
)


class AuditFindingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, finding: AuditFinding) -> AuditFinding:
        self.db.add(finding)
        await self.db.flush()
        return finding

    async def get_by_id_for_company(
        self, finding_id: uuid.UUID, company_id: uuid.UUID
    ) -> AuditFinding | None:
        result = await self.db.execute(
            select(AuditFinding)
            .options(selectinload(AuditFinding.evidence))
            .where(AuditFinding.id == finding_id, AuditFinding.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_for_engagement(
        self,
        engagement_id: uuid.UUID,
        *,
        status: AuditFindingStatus | None = None,
        severity: AuditFindingSeverity | None = None,
        category: AuditFindingCategory | None = None,
        assigned_to: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AuditFinding], int]:
        query = select(AuditFinding).where(AuditFinding.engagement_id == engagement_id)
        if status is not None:
            query = query.where(AuditFinding.status == status)
        if severity is not None:
            query = query.where(AuditFinding.severity == severity)
        if category is not None:
            query = query.where(AuditFinding.category == category)
        if assigned_to is not None:
            query = query.where(AuditFinding.assigned_to == assigned_to)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(AuditFinding.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        status: AuditFindingStatus | None = None,
        assigned_to: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AuditFinding], int]:
        query = select(AuditFinding).where(AuditFinding.company_id == company_id)
        if status is not None:
            query = query.where(AuditFinding.status == status)
        if assigned_to is not None:
            query = query.where(AuditFinding.assigned_to == assigned_to)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(AuditFinding.due_date.asc().nulls_last()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def find_potential_duplicates(
        self,
        engagement_id: uuid.UUID,
        *,
        source_type: AuditFindingSourceType | None,
        source_id: uuid.UUID | None,
    ) -> list[AuditFinding]:
        """Findings already open against the same source record (PHASE7
        §42) — used to warn, never to block, since two genuinely distinct
        issues can share one source record."""
        if source_type is None or source_id is None:
            return []
        result = await self.db.execute(
            select(AuditFinding).where(
                AuditFinding.engagement_id == engagement_id,
                AuditFinding.source_type == source_type,
                AuditFinding.source_id == source_id,
                AuditFinding.status.notin_(
                    [AuditFindingStatus.RESOLVED, AuditFindingStatus.CLOSED, AuditFindingStatus.REJECTED]
                ),
            )
        )
        return list(result.scalars().all())

    async def next_finding_code(self, engagement_id: uuid.UUID) -> str:
        count_result = await self.db.execute(
            select(func.count()).select_from(AuditFinding).where(AuditFinding.engagement_id == engagement_id)
        )
        count = count_result.scalar_one()
        return f"F-{count + 1:03d}"

    async def count_by_status_for_engagement(self, engagement_id: uuid.UUID) -> dict[AuditFindingStatus, int]:
        result = await self.db.execute(
            select(AuditFinding.status, func.count())
            .where(AuditFinding.engagement_id == engagement_id)
            .group_by(AuditFinding.status)
        )
        return dict(result.all())
