import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_enums import (
    ComplianceCategory,
    ComplianceModule,
    CompliancePriority,
    ComplianceTaskStatus,
)
from app.models.compliance_task import ComplianceTask, ComplianceTaskComment, ComplianceTaskEvidence

_OPEN_STATUSES = (
    ComplianceTaskStatus.PENDING,
    ComplianceTaskStatus.IN_PROGRESS,
    ComplianceTaskStatus.PENDING_REVIEW,
    ComplianceTaskStatus.OVERDUE,
)


class ComplianceTaskRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, task: ComplianceTask) -> ComplianceTask:
        self.db.add(task)
        await self.db.flush()
        return task

    async def get_by_id_for_company(self, task_id: uuid.UUID, company_id: uuid.UUID) -> ComplianceTask | None:
        result = await self.db.execute(
            select(ComplianceTask).where(ComplianceTask.id == task_id, ComplianceTask.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        status: ComplianceTaskStatus | None = None,
        category: ComplianceCategory | None = None,
        module: ComplianceModule | None = None,
        priority: CompliancePriority | None = None,
        assigned_to: uuid.UUID | None = None,
        reviewer_id: uuid.UUID | None = None,
        due_before: date | None = None,
        due_after: date | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ComplianceTask], int]:
        query = select(ComplianceTask).where(ComplianceTask.company_id == company_id)
        if status is not None:
            query = query.where(ComplianceTask.status == status)
        if category is not None:
            query = query.where(ComplianceTask.category == category)
        if module is not None:
            query = query.where(ComplianceTask.module == module)
        if priority is not None:
            query = query.where(ComplianceTask.priority == priority)
        if assigned_to is not None:
            query = query.where(ComplianceTask.assigned_to == assigned_to)
        if reviewer_id is not None:
            query = query.where(ComplianceTask.reviewer_id == reviewer_id)
        if due_before is not None:
            query = query.where(ComplianceTask.due_date <= due_before)
        if due_after is not None:
            query = query.where(ComplianceTask.due_date >= due_after)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(ComplianceTask.title.ilike(pattern), ComplianceTask.description.ilike(pattern))
            )

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(ComplianceTask.due_date.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_open_for_sweep(self, company_id: uuid.UUID) -> list[ComplianceTask]:
        result = await self.db.execute(
            select(ComplianceTask).where(
                ComplianceTask.company_id == company_id,
                ComplianceTask.status.in_([ComplianceTaskStatus.PENDING, ComplianceTaskStatus.IN_PROGRESS, ComplianceTaskStatus.PENDING_REVIEW]),
            )
        )
        return list(result.scalars().all())

    async def count_by_status(self, company_id: uuid.UUID) -> dict[ComplianceTaskStatus, int]:
        result = await self.db.execute(
            select(ComplianceTask.status, func.count())
            .where(ComplianceTask.company_id == company_id)
            .group_by(ComplianceTask.status)
        )
        return dict(result.all())

    async def count_by_category(self, company_id: uuid.UUID) -> dict[ComplianceCategory, int]:
        result = await self.db.execute(
            select(ComplianceTask.category, func.count())
            .where(ComplianceTask.company_id == company_id, ComplianceTask.status.in_(_OPEN_STATUSES))
            .group_by(ComplianceTask.category)
        )
        return dict(result.all())

    async def count_by_priority(self, company_id: uuid.UUID) -> dict[CompliancePriority, int]:
        result = await self.db.execute(
            select(ComplianceTask.priority, func.count())
            .where(ComplianceTask.company_id == company_id, ComplianceTask.status.in_(_OPEN_STATUSES))
            .group_by(ComplianceTask.priority)
        )
        return dict(result.all())

    async def list_due_in_range(self, company_id: uuid.UUID, *, start: date, end: date) -> list[ComplianceTask]:
        result = await self.db.execute(
            select(ComplianceTask)
            .where(
                ComplianceTask.company_id == company_id,
                ComplianceTask.due_date >= start,
                ComplianceTask.due_date <= end,
            )
            .order_by(ComplianceTask.due_date.asc())
        )
        return list(result.scalars().all())


class ComplianceTaskCommentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, comment: ComplianceTaskComment) -> ComplianceTaskComment:
        self.db.add(comment)
        await self.db.flush()
        return comment

    async def list_for_task(self, task_id: uuid.UUID) -> list[ComplianceTaskComment]:
        result = await self.db.execute(
            select(ComplianceTaskComment)
            .where(ComplianceTaskComment.task_id == task_id)
            .order_by(ComplianceTaskComment.created_at.asc())
        )
        return list(result.scalars().all())


class ComplianceTaskEvidenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, evidence: ComplianceTaskEvidence) -> ComplianceTaskEvidence:
        self.db.add(evidence)
        await self.db.flush()
        return evidence

    async def get_by_id_for_company(
        self, evidence_id: uuid.UUID, company_id: uuid.UUID
    ) -> ComplianceTaskEvidence | None:
        result = await self.db.execute(
            select(ComplianceTaskEvidence).where(
                ComplianceTaskEvidence.id == evidence_id, ComplianceTaskEvidence.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_task(self, task_id: uuid.UUID) -> list[ComplianceTaskEvidence]:
        result = await self.db.execute(
            select(ComplianceTaskEvidence)
            .where(ComplianceTaskEvidence.task_id == task_id)
            .order_by(ComplianceTaskEvidence.created_at.asc())
        )
        return list(result.scalars().all())

    async def delete(self, evidence: ComplianceTaskEvidence) -> None:
        await self.db.delete(evidence)
        await self.db.flush()
