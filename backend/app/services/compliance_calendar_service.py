"""Calendar and dashboard aggregation (PHASE9 §21, §27, PHASE13 §17).

Aggregates both Compliance Tasks and Compliance Obligations into the calendar
day buckets, respecting tenant isolation and date range parameters.
"""

import calendar
import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_enums import (
    ComplianceCategory,
    ComplianceObligationStatus,
    CompliancePriority,
    ComplianceTaskStatus,
)
from app.models.user import User
from app.repositories.compliance_obligation_repository import ComplianceObligationRepository
from app.repositories.compliance_task_repository import ComplianceTaskRepository
from app.schemas.compliance_calendar import CalendarDay, CalendarItem, ComplianceDashboard
from app.services.compliance_task_service import ComplianceTaskService, is_overdue

_TERMINAL_TASK_STATUSES = {
    ComplianceTaskStatus.COMPLETED,
    ComplianceTaskStatus.VERIFIED,
    ComplianceTaskStatus.CANCELLED,
    ComplianceTaskStatus.LOCKED,
}

_TERMINAL_OBLIGATION_STATUSES = {
    ComplianceObligationStatus.COMPLETED,
    ComplianceObligationStatus.FULFILLED,
    ComplianceObligationStatus.CANCELLED,
}


class ComplianceCalendarService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.task_repo = ComplianceTaskRepository(db)
        self.obligation_repo = ComplianceObligationRepository(db)
        self.tasks = ComplianceTaskService(db)

    async def calendar_range(self, company_id: uuid.UUID, *, start: date, end: date) -> list[CalendarDay]:
        tasks = await self.task_repo.list_due_in_range(company_id, start=start, end=end)
        obligations = await self.obligation_repo.list_due_in_range(company_id, start=start, end=end)

        by_day: dict[date, list[CalendarItem]] = {}
        today = date.today()

        for task in tasks:
            by_day.setdefault(task.due_date, []).append(
                CalendarItem(
                    task_id=task.id,
                    obligation_id=uuid.UUID(str(task.obligation_id)) if task.obligation_id else None,
                    item_type="TASK",
                    title=task.title,
                    category=task.category,
                    priority=task.priority,
                    status=task.status.value,
                    is_overdue=is_overdue(task),
                )
            )

        for ob in obligations:
            is_ob_overdue = (
                ob.status == ComplianceObligationStatus.OVERDUE
                or (ob.due_date < today and ob.status not in _TERMINAL_OBLIGATION_STATUSES)
            )
            by_day.setdefault(ob.due_date, []).append(
                CalendarItem(
                    obligation_id=ob.id,
                    item_type="OBLIGATION",
                    title=f"[{ob.code}] {ob.name}",
                    category=ob.category,
                    priority=ob.priority,
                    status=ob.status.value,
                    is_overdue=is_ob_overdue,
                )
            )

        return [CalendarDay(date=day, items=items) for day, items in sorted(by_day.items())]

    async def calendar_month(self, company_id: uuid.UUID, *, year: int, month: int) -> list[CalendarDay]:
        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)
        return await self.calendar_range(company_id, start=start, end=end)

    async def calendar_week(self, company_id: uuid.UUID, *, start: date) -> list[CalendarDay]:
        return await self.calendar_range(company_id, start=start, end=start + timedelta(days=6))

    async def dashboard(self, company_id: uuid.UUID, current_user: User) -> ComplianceDashboard:
        await self.tasks.sweep_overdue(company_id, current_user)

        status_counts = await self.task_repo.count_by_status(company_id)
        category_counts = await self.task_repo.count_by_category(company_id)
        priority_counts = await self.task_repo.count_by_priority(company_id)

        today = date.today()
        week_end = today + timedelta(days=7)
        due_today_tasks = await self.task_repo.list_due_in_range(company_id, start=today, end=today)
        due_week_tasks = await self.task_repo.list_due_in_range(company_id, start=today, end=week_end)

        total_open = sum(count for status, count in status_counts.items() if status not in _TERMINAL_TASK_STATUSES)
        critical_tasks = priority_counts.get(CompliancePriority.CRITICAL, 0)

        return ComplianceDashboard(
            total_open=total_open,
            due_today=len(due_today_tasks),
            due_this_week=len(due_week_tasks),
            overdue=status_counts.get(ComplianceTaskStatus.OVERDUE, 0),
            pending_review=status_counts.get(ComplianceTaskStatus.PENDING_REVIEW, 0),
            completed=status_counts.get(ComplianceTaskStatus.COMPLETED, 0),
            verified=status_counts.get(ComplianceTaskStatus.VERIFIED, 0),
            critical_tasks=critical_tasks,
            by_category={cat: category_counts.get(cat, 0) for cat in ComplianceCategory},
            by_priority={pri: priority_counts.get(pri, 0) for pri in CompliancePriority},
        )
