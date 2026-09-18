import uuid

from pydantic import BaseModel

from app.models.audit_workflow_enums import AuditEngagementStatus, AuditFindingSeverity, AuditFindingStatus
from app.schemas.audit_engagement import AuditEngagementRead


class AuditEngagementProgress(BaseModel):
    engagement: AuditEngagementRead
    checklist_total: int
    checklist_completed: int
    findings_total: int
    findings_open: int
    findings_by_severity: dict[AuditFindingSeverity, int]


class AuditReviewQueueItem(BaseModel):
    engagement: AuditEngagementRead
    open_findings: int
    high_or_critical_open_findings: int
    pending_responses: int


class AuditWorkflowDashboard(BaseModel):
    engagements_by_status: dict[AuditEngagementStatus, int]
    findings_by_status: dict[AuditFindingStatus, int]
    review_queue: list[AuditReviewQueueItem]


class AuditFindingExportRow(BaseModel):
    engagement_code: str
    finding_code: str
    title: str
    category: str
    severity: str
    status: str
    assigned_to: uuid.UUID | None
    due_date: str | None
