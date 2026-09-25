"""Read-only reporting and the cross-engagement review queue (PHASE7 §14,
§53). Reuses the same engagement/finding/checklist repositories the
workflow itself uses, so a report can never show numbers the engagement
screens themselves couldn't produce, and export reuses the shared
CSV/XLSX writers already established in Phase 4/5/6 rather than
reimplementing file generation a fourth time.
"""

import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.audit_workflow_enums import (
    AuditChecklistItemStatus,
    AuditEngagementStatus,
    AuditFindingResponseStatus,
    AuditFindingSeverity,
    AuditFindingStatus,
)
from app.repositories.audit_checklist_repository import AuditChecklistRepository
from app.repositories.audit_engagement_repository import AuditEngagementRepository
from app.repositories.audit_finding_evidence_repository import AuditFindingResponseRepository
from app.repositories.audit_finding_repository import AuditFindingRepository
from app.schemas.audit_engagement import AuditEngagementRead
from app.schemas.audit_report import (
    AuditEngagementProgress,
    AuditReviewQueueItem,
    AuditWorkflowDashboard,
)
from app.utils.export import ExportFile, ExportFormat, ExportSection, write_csv, write_xlsx

_OPEN_FINDING_STATUSES = {
    AuditFindingStatus.OPEN,
    AuditFindingStatus.ASSIGNED,
    AuditFindingStatus.IN_REVIEW,
    AuditFindingStatus.ACTION_REQUIRED,
    AuditFindingStatus.RESPONSE_SUBMITTED,
    AuditFindingStatus.REOPENED,
}


class AuditWorkflowReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.engagements = AuditEngagementRepository(db)
        self.findings = AuditFindingRepository(db)
        self.checklists = AuditChecklistRepository(db)
        self.responses = AuditFindingResponseRepository(db)

    async def engagement_progress(self, company_id: uuid.UUID, engagement_id: uuid.UUID) -> AuditEngagementProgress:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")

        checklist = await self.checklists.get_for_engagement(engagement_id, company_id)
        checklist_total = len(checklist.items) if checklist else 0
        checklist_completed = (
            sum(1 for i in checklist.items if i.status == AuditChecklistItemStatus.COMPLETED) if checklist else 0
        )

        all_findings, findings_total = await self.findings.list_for_engagement(engagement_id, offset=0, limit=1000)
        findings_open = sum(1 for f in all_findings if f.status in _OPEN_FINDING_STATUSES)
        findings_by_severity = {severity: 0 for severity in AuditFindingSeverity}
        for f in all_findings:
            findings_by_severity[f.severity] += 1

        return AuditEngagementProgress(
            engagement=AuditEngagementRead.model_validate(engagement),
            checklist_total=checklist_total,
            checklist_completed=checklist_completed,
            findings_total=findings_total,
            findings_open=findings_open,
            findings_by_severity=findings_by_severity,
        )

    async def dashboard(self, company_id: uuid.UUID) -> AuditWorkflowDashboard:
        engagements_by_status = {status: 0 for status in AuditEngagementStatus}
        findings_by_status = {status: 0 for status in AuditFindingStatus}

        offset = 0
        review_queue: list[AuditReviewQueueItem] = []
        while True:
            engagements, total = await self.engagements.list_for_company(company_id, offset=offset, limit=100)
            if not engagements:
                break
            for engagement in engagements:
                engagements_by_status[engagement.status] += 1

                findings, _total = await self.findings.list_for_engagement(engagement.id, offset=0, limit=1000)
                for f in findings:
                    findings_by_status[f.status] += 1

                if engagement.status in (
                    AuditEngagementStatus.PENDING_AUDITOR_REVIEW,
                    AuditEngagementStatus.IN_REVIEW,
                ):
                    open_findings = sum(1 for f in findings if f.status in _OPEN_FINDING_STATUSES)
                    high_or_critical_open = sum(
                        1
                        for f in findings
                        if f.status in _OPEN_FINDING_STATUSES
                        and f.severity in (AuditFindingSeverity.HIGH, AuditFindingSeverity.CRITICAL)
                    )
                    pending_responses = 0
                    for f in findings:
                        responses = await self.responses.list_for_finding(f.id)
                        pending_responses += sum(
                            1 for r in responses if r.status == AuditFindingResponseStatus.SUBMITTED
                        )
                    review_queue.append(
                        AuditReviewQueueItem(
                            engagement=AuditEngagementRead.model_validate(engagement),
                            open_findings=open_findings,
                            high_or_critical_open_findings=high_or_critical_open,
                            pending_responses=pending_responses,
                        )
                    )
            offset += 100
            if offset >= total:
                break

        return AuditWorkflowDashboard(
            engagements_by_status=engagements_by_status,
            findings_by_status=findings_by_status,
            review_queue=review_queue,
        )

    async def export_engagement_findings(
        self, company_id: uuid.UUID, engagement_id: uuid.UUID, fmt: ExportFormat
    ) -> ExportFile:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")

        findings, _total = await self.findings.list_for_engagement(engagement_id, offset=0, limit=1000)
        sections = [
            ExportSection(
                "Findings",
                ["Finding Code", "Title", "Category", "Severity", "Status", "Assigned To", "Due Date"],
                [
                    [
                        f.finding_code,
                        f.title,
                        f.category.value,
                        f.severity.value,
                        f.status.value,
                        str(f.assigned_to) if f.assigned_to else "",
                        f.due_date.isoformat() if f.due_date else "",
                    ]
                    for f in findings
                ],
            )
        ]

        period_label = f"{engagement.period_start} to {engagement.period_end}"
        if fmt == "xlsx":
            content = write_xlsx(
                report_type="Audit Findings Report", gstin=engagement.engagement_code,
                period_label=period_label, sections=sections,
            )
            return ExportFile(
                content=content,
                filename=f"audit-findings-{engagement.engagement_code}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        content = write_csv(
            report_type="Audit Findings Report", gstin=engagement.engagement_code,
            period_label=period_label, sections=sections,
        )
        return ExportFile(
            content=content, filename=f"audit-findings-{engagement.engagement_code}.csv", media_type="text/csv"
        )
