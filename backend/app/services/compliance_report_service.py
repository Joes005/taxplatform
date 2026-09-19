"""Compliance reporting and export (PHASE9 §36-37). Reuses the same
`ComplianceTaskRepository` the task list/calendar screens use, and the
shared CSV/XLSX writers already established in Phase 4/5/6/7/8, rather
than a sixth implementation of file generation.
"""

import uuid
from datetime import date
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_enums import ComplianceCategory, ComplianceModule, CompliancePriority, ComplianceTaskStatus
from app.repositories.compliance_task_repository import ComplianceTaskRepository
from app.services.compliance_task_service import is_overdue
from app.services.gst_export_service import ExportFile, ExportSection, write_csv, write_xlsx

ExportFormat = Literal["csv", "xlsx"]


class ComplianceReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ComplianceTaskRepository(db)

    async def export_tasks(
        self,
        company_id: uuid.UUID,
        fmt: ExportFormat,
        *,
        status: ComplianceTaskStatus | None = None,
        category: ComplianceCategory | None = None,
        module: ComplianceModule | None = None,
        priority: CompliancePriority | None = None,
        overdue_only: bool = False,
    ) -> ExportFile:
        tasks, _total = await self.repo.list_for_company(
            company_id, status=status, category=category, module=module, priority=priority, offset=0, limit=5000
        )
        if overdue_only:
            tasks = [t for t in tasks if is_overdue(t)]

        sections = [
            ExportSection(
                "Compliance Tasks",
                ["Title", "Category", "Module", "Priority", "Status", "Due Date", "Assigned To", "Overdue"],
                [
                    [
                        t.title,
                        t.category.value,
                        t.module.value,
                        t.priority.value,
                        t.status.value,
                        t.due_date.isoformat(),
                        str(t.assigned_to) if t.assigned_to else "",
                        "YES" if is_overdue(t) else "NO",
                    ]
                    for t in tasks
                ],
            )
        ]

        label = f"Generated {date.today().isoformat()}"
        if fmt == "xlsx":
            content = write_xlsx(report_type="Compliance Task Report", gstin="", period_label=label, sections=sections)
            return ExportFile(
                content=content,
                filename="compliance-tasks.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        content = write_csv(report_type="Compliance Task Report", gstin="", period_label=label, sections=sections)
        return ExportFile(content=content, filename="compliance-tasks.csv", media_type="text/csv")
