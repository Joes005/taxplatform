import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AttentionSummary(BaseModel):
    critical_count: int = 0
    high_priority_count: int = 0
    due_soon_count: int = 0
    pending_review_count: int = 0
    overdue_count: int = 0
    completed_count: int = 0


class DashboardSummary(BaseModel):
    company_id: uuid.UUID
    company_name: str
    financial_year: str | None = None
    financial_year_id: uuid.UUID | None = None
    active_period: str | None = None
    last_data_update: datetime | None = None
    attention: AttentionSummary
    role: str


class DashboardActionItem(BaseModel):
    id: str
    title: str
    description: str
    module: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str
    due_date: str | None = None
    created_date: str | None = None
    status: str
    target_url: str
    responsible_roles: list[str] = Field(default_factory=list)
    source_reference: str | None = None


class WorkflowStage(BaseModel):
    stage_key: str
    name: str
    status: str  # COMPLETE, IN_PROGRESS, BLOCKED, NOT_STARTED
    pending_count: int = 0
    blocking_count: int = 0
    next_action_label: str | None = None
    next_action_url: str | None = None


class SetupStep(BaseModel):
    key: str
    label: str
    completed: bool
    description: str
    target_url: str


class SetupProgress(BaseModel):
    completed_count: int
    total_count: int
    is_all_complete: bool
    steps: list[SetupStep]


class HealthAreaStatus(BaseModel):
    area: str
    status: str  # READY, NEEDS_ATTENTION, BLOCKED, NOT_CONFIGURED
    message: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    target_url: str


class CompanyHealth(BaseModel):
    overall_status: str  # READY, NEEDS_ATTENTION, BLOCKED, NOT_CONFIGURED
    areas: list[HealthAreaStatus]


class ActionCenterItem(BaseModel):
    id: str
    title: str
    description: str
    module: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str
    due_date: str | None = None
    created_date: str | None = None
    status: str
    target_url: str
    responsible_roles: list[str] = Field(default_factory=list)
    source_reference: str | None = None
