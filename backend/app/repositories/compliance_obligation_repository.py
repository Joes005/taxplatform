import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_enums import ComplianceCategory, ComplianceModule, ComplianceObligationStatus
from app.models.compliance_obligation import ComplianceObligation


class ComplianceObligationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, obligation: ComplianceObligation) -> ComplianceObligation:
        self.db.add(obligation)
        await self.db.flush()
        await self.db.refresh(obligation)
        return obligation

    async def get_by_id_for_company(
        self, obligation_id: uuid.UUID, company_id: uuid.UUID
    ) -> ComplianceObligation | None:
        result = await self.db.execute(
            select(ComplianceObligation).where(
                ComplianceObligation.id == obligation_id, ComplianceObligation.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_natural_key(
        self, company_id: uuid.UUID, code: str, financial_year_id: uuid.UUID | None, tax_period: str | None
    ) -> ComplianceObligation | None:
        result = await self.db.execute(
            select(ComplianceObligation).where(
                ComplianceObligation.company_id == company_id,
                ComplianceObligation.code == code,
                ComplianceObligation.financial_year_id == financial_year_id,
                ComplianceObligation.tax_period == tax_period,
            )
        )
        return result.scalar_one_or_none()

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
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ComplianceObligation], int]:
        query = select(ComplianceObligation).where(ComplianceObligation.company_id == company_id)
        if category is not None:
            query = query.where(ComplianceObligation.category == category)
        if module is not None:
            query = query.where(ComplianceObligation.module == module)
        if status is not None:
            query = query.where(ComplianceObligation.status == status)
        if readiness_status is not None:
            query = query.where(ComplianceObligation.readiness_status == readiness_status)
        if assigned_to is not None:
            query = query.where(ComplianceObligation.assigned_to == assigned_to)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(
                or_(
                    ComplianceObligation.code.ilike(s),
                    ComplianceObligation.name.ilike(s),
                    ComplianceObligation.description.ilike(s),
                )
            )
        if overdue_only:
            today = date.today()
            query = query.where(
                ComplianceObligation.due_date < today,
                ComplianceObligation.status.notin_([
                    ComplianceObligationStatus.COMPLETED,
                    ComplianceObligationStatus.FULFILLED,
                    ComplianceObligationStatus.CANCELLED,
                ]),
            )
        if active_only:
            query = query.where(ComplianceObligation.active.is_(True))

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(ComplianceObligation.due_date.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_due_in_range(
        self, company_id: uuid.UUID, *, start: date, end: date
    ) -> list[ComplianceObligation]:
        result = await self.db.execute(
            select(ComplianceObligation).where(
                ComplianceObligation.company_id == company_id,
                ComplianceObligation.active.is_(True),
                ComplianceObligation.due_date >= start,
                ComplianceObligation.due_date <= end,
            ).order_by(ComplianceObligation.due_date.asc())
        )
        return list(result.scalars().all())

    async def list_open_past_due(
        self, company_id: uuid.UUID, *, as_of: date
    ) -> list[ComplianceObligation]:
        closed_statuses = [
            ComplianceObligationStatus.COMPLETED,
            ComplianceObligationStatus.FULFILLED,
            ComplianceObligationStatus.CANCELLED,
        ]
        result = await self.db.execute(
            select(ComplianceObligation).where(
                ComplianceObligation.company_id == company_id,
                ComplianceObligation.active.is_(True),
                ComplianceObligation.due_date < as_of,
                ComplianceObligation.status.notin_(closed_statuses),
            )
        )
        return list(result.scalars().all())

