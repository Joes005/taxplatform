"""Local CSV/XLSX export of TDS preparation/reconciliation reports
(PHASE5 section 60). Every export is clearly labeled a "Preparation" or
"Reconciliation Report" — never "Filed Return" — reusing the same
rendering helpers Phase 4's `GSTExportService` established rather than
reimplementing CSV/XLSX writing a second time.
"""

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.repositories.tds_profile_repository import TDSProfileRepository
from app.repositories.tds_reconciliation_repository import TDSReconciliationRepository
from app.repositories.tds_return_period_repository import TDSReturnPeriodRepository
from app.services.tds_report_service import TDSReportService
from app.utils.export import ExportFile, ExportFormat, ExportSection, write_csv, write_xlsx


class TDSExportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.profile_repo = TDSProfileRepository(db)
        self.period_repo = TDSReturnPeriodRepository(db)
        self.recon_repo = TDSReconciliationRepository(db)
        self.reports = TDSReportService(db)

    async def _period_context(self, company_id, return_period_id):
        profile = await self.profile_repo.get_for_company(company_id)
        if profile is None:
            raise ValidationAppError(
                "A TDS profile is required before exporting reports", code="TDS_PROFILE_REQUIRED"
            )
        period = await self.period_repo.get_by_id_for_company(return_period_id, company_id)
        if period is None:
            raise NotFoundError("TDS return period not found", code="TDS_RETURN_PERIOD_NOT_FOUND")
        return profile.tan, f"{period.quarter.value} {period.period_start.year}", period

    def _render(self, *, report_type, tan, period_label, sections, fmt: ExportFormat, filename_stub) -> ExportFile:
        if fmt == "xlsx":
            content = write_xlsx(report_type=report_type, gstin=tan, period_label=period_label, sections=sections)
            return ExportFile(
                content=content,
                filename=f"{filename_stub}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        content = write_csv(report_type=report_type, gstin=tan, period_label=period_label, sections=sections)
        return ExportFile(content=content, filename=f"{filename_stub}.csv", media_type="text/csv")

    async def export_quarterly_summary(self, company_id, return_period_id, fmt: ExportFormat) -> ExportFile:
        tan, period_label, period = await self._period_context(company_id, return_period_id)
        quarterly = await self.reports.quarterly_summary(company_id, period.period_start, period.period_end)
        by_section = await self.reports.section_summary(company_id, period.period_start, period.period_end)
        by_deductee = await self.reports.deductee_summary(company_id, period.period_start, period.period_end)

        sections = [
            ExportSection(
                "Quarterly Summary",
                ["Transactions", "Deductees", "Gross Amount", "TDS Deducted", "TDS Paid", "Outstanding", "Review Required"],
                [[
                    quarterly.transaction_count, quarterly.deductee_count, quarterly.gross_amount,
                    quarterly.tds_deducted, quarterly.tds_paid, quarterly.tds_outstanding,
                    quarterly.review_required_count,
                ]],
            ),
            ExportSection(
                "By Section",
                ["Section", "Transactions", "Gross Amount", "TDS Deducted", "TDS Paid", "Outstanding"],
                [[r.section_code, r.transaction_count, r.gross_amount, r.tds_deducted, r.tds_paid, r.tds_outstanding] for r in by_section],
            ),
            ExportSection(
                "By Deductee",
                ["Deductee", "PAN", "Transactions", "Gross Amount", "TDS Deducted", "TDS Paid", "Outstanding"],
                [[r.deductee_name, r.pan, r.transaction_count, r.gross_amount, r.tds_deducted, r.tds_paid, r.tds_outstanding] for r in by_deductee],
            ),
        ]
        return self._render(
            report_type="TDS Quarterly Preparation Report",
            tan=tan,
            period_label=period_label,
            sections=sections,
            fmt=fmt,
            filename_stub=f"tds-quarterly-preparation-{period_label.replace(' ', '-')}",
        )

    async def export_reconciliation(self, company_id, return_period_id, fmt: ExportFormat) -> ExportFile:
        tan, period_label, period = await self._period_context(company_id, return_period_id)
        rows, _total = await self.recon_repo.list_for_company(
            company_id, financial_year_id=period.financial_year_id, offset=0, limit=100000
        )

        sections = [
            ExportSection(
                "Reconciliation Findings",
                ["Status", "TDS Transaction", "Challan", "Expected", "Allocated", "Variance"],
                [[
                    r.status.value, str(r.tds_transaction_id) if r.tds_transaction_id else "",
                    str(r.tds_challan_id) if r.tds_challan_id else "",
                    r.expected_amount, r.allocated_amount, r.variance_amount,
                ] for r in rows],
            ),
        ]
        return self._render(
            report_type="TDS Reconciliation Report",
            tan=tan,
            period_label=period_label,
            sections=sections,
            fmt=fmt,
            filename_stub=f"tds-reconciliation-{period_label.replace(' ', '-')}",
        )
