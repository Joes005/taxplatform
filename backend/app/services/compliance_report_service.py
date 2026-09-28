"""Compliance reporting and export (PHASE9 §36-37, PHASE13 §21).

Reuses the shared CSV/XLSX writers in app.utils.export.
Exports:
- Compliance Tasks
- Compliance Obligations
- Compliance Readiness Checks
"""

import uuid
from datetime import date
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_enums import (
    ComplianceCategory,
    ComplianceModule,
    ComplianceObligationStatus,
    CompliancePriority,
    ComplianceTaskStatus,
)
from app.repositories.compliance_obligation_repository import ComplianceObligationRepository
from app.repositories.compliance_task_repository import ComplianceTaskRepository
from app.services.compliance_readiness_service import ComplianceReadinessService
from app.services.compliance_task_service import is_overdue
from app.utils.export import ExportFile, ExportFormat, ExportSection, write_csv, write_xlsx


class ComplianceReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.task_repo = ComplianceTaskRepository(db)
        self.obligation_repo = ComplianceObligationRepository(db)
        self.readiness = ComplianceReadinessService(db)

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
        tasks, _total = await self.task_repo.list_for_company(
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

    async def export_obligations(
        self,
        company_id: uuid.UUID,
        fmt: ExportFormat,
        *,
        status: ComplianceObligationStatus | None = None,
        category: ComplianceCategory | None = None,
        module: ComplianceModule | None = None,
        overdue_only: bool = False,
    ) -> ExportFile:
        obligations, _total = await self.obligation_repo.list_for_company(
            company_id,
            status=status,
            category=category,
            module=module,
            overdue_only=overdue_only,
            active_only=True,
            offset=0,
            limit=5000,
        )

        today = date.today()
        sections = [
            ExportSection(
                "Compliance Obligations",
                ["Code", "Name", "Category", "Module", "Frequency", "Due Date", "Status", "Readiness", "Assigned To", "Overdue"],
                [
                    [
                        ob.code,
                        ob.name,
                        ob.category.value,
                        ob.module.value,
                        ob.frequency.value,
                        ob.due_date.isoformat(),
                        ob.status.value,
                        ob.readiness_status,
                        str(ob.assigned_to) if ob.assigned_to else "",
                        "YES" if (ob.status == ComplianceObligationStatus.OVERDUE or ob.due_date < today) else "NO",
                    ]
                    for ob in obligations
                ],
            )
        ]

        label = f"Generated {today.isoformat()}"
        if fmt == "xlsx":
            content = write_xlsx(report_type="Compliance Obligations Report", gstin="", period_label=label, sections=sections)
            return ExportFile(
                content=content,
                filename="compliance-obligations.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        content = write_csv(report_type="Compliance Obligations Report", gstin="", period_label=label, sections=sections)
        return ExportFile(content=content, filename="compliance-obligations.csv", media_type="text/csv")

    async def export_readiness(
        self,
        company_id: uuid.UUID,
        fmt: ExportFormat,
    ) -> ExportFile:
        obligations, _total = await self.obligation_repo.list_for_company(
            company_id,
            active_only=True,
            offset=0,
            limit=500,
        )

        rows = []
        for ob in obligations:
            readiness_res = await self.readiness.evaluate_obligation(company_id, ob)
            for chk in readiness_res.checks:
                rows.append([
                    ob.code,
                    ob.name,
                    readiness_res.overall_status.value,
                    chk.check_code,
                    chk.description,
                    chk.status,
                    "YES" if chk.blocking else "NO",
                    chk.remediation_action,
                ])

        sections = [
            ExportSection(
                "Compliance Readiness Checks",
                ["Obligation Code", "Obligation Name", "Overall Readiness", "Check Code", "Description", "Status", "Blocking", "Remediation Action"],
                rows,
            )
        ]

        label = f"Generated {date.today().isoformat()}"
        if fmt == "xlsx":
            content = write_xlsx(report_type="Compliance Readiness Report", gstin="", period_label=label, sections=sections)
            return ExportFile(
                content=content,
                filename="compliance-readiness.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        content = write_csv(report_type="Compliance Readiness Report", gstin="", period_label=label, sections=sections)
        return ExportFile(content=content, filename="compliance-readiness.csv", media_type="text/csv")
