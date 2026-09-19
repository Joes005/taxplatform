import uuid
from datetime import date

from pydantic import BaseModel

from app.models.compliance_enums import (
    ComplianceCategory,
    CompliancePriority,
    ComplianceTaskStatus,
)


class CalendarItem(BaseModel):
    task_id: uuid.UUID
    title: str
    category: ComplianceCategory
    priority: CompliancePriority
    status: ComplianceTaskStatus
    is_overdue: bool


class CalendarDay(BaseModel):
    date: date
    items: list[CalendarItem]


class ComplianceDashboard(BaseModel):
    total_open: int
    due_today: int
    due_this_week: int
    overdue: int
    pending_review: int
    completed: int
    verified: int
    critical_tasks: int
    by_category: dict[ComplianceCategory, int]
    by_priority: dict[CompliancePriority, int]
