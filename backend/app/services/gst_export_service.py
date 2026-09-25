"""Local CSV/XLSX export of GST preparation reports (PHASE4 section 54).

Every export is clearly labeled a "Preparation" or "Reconciliation Report"
— never "Filed Return" — and always carries company GSTIN, return period,
and a generation timestamp, so nobody mistakes a local working file for an
actual filing (PHASE4 sections 74, 78).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.repositories.gst_profile_repository import GSTProfileRepository
from app.repositories.gst_reconciliation_repository import GSTReconciliationRepository
from app.repositories.gst_return_period_repository import GSTReturnPeriodRepository
from app.services.gstr1_service import GSTR1Service
from app.services.gstr3b_service import GSTR3BService
from app.services.itc_service import ITCService
from app.utils.export import (
    ExportFile,
    ExportFormat,
    ExportSection,
    write_csv,
    write_xlsx,
)


class GSTExportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.profile_repo = GSTProfileRepository(db)
        self.period_repo = GSTReturnPeriodRepository(db)
        self.gstr1 = GSTR1Service(db)
        self.gstr3b = GSTR3BService(db)
        self.itc = ITCService(db)
        self.recon_repo = GSTReconciliationRepository(db)

    async def _period_context(self, company_id, return_period_id) -> tuple[str, str]:
        profile = await self.profile_repo.get_for_company(company_id)
        if profile is None:
            raise ValidationAppError(
                "A GST profile is required before exporting reports", code="GST_PROFILE_REQUIRED"
            )
        period = await self.period_repo.get_by_id_for_company(return_period_id, company_id)
        if period is None:
            raise NotFoundError("GST return period not found", code="GST_RETURN_PERIOD_NOT_FOUND")
        return profile.gstin, f"{period.month:02d}/{period.year}"

    def _render(self, *, report_type: str, gstin: str, period_label: str, sections, fmt: ExportFormat, filename_stub: str) -> ExportFile:
        if fmt == "xlsx":
            content = write_xlsx(report_type=report_type, gstin=gstin, period_label=period_label, sections=sections)
            return ExportFile(
                content=content,
                filename=f"{filename_stub}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        content = write_csv(report_type=report_type, gstin=gstin, period_label=period_label, sections=sections)
        return ExportFile(content=content, filename=f"{filename_stub}.csv", media_type="text/csv")

    async def export_gstr1(self, company_id, return_period_id, fmt: ExportFormat) -> ExportFile:
        gstin, period_label = await self._period_context(company_id, return_period_id)

        b2b = await self.gstr1.get_b2b(company_id, return_period_id)
        b2c_large = await self.gstr1.get_b2c_large(company_id, return_period_id)
        b2c_others = await self.gstr1.get_b2c_others(company_id, return_period_id)
        exports = await self.gstr1.get_exports(company_id, return_period_id)
        credit_notes = await self.gstr1.get_credit_notes(company_id, return_period_id)
        debit_notes = await self.gstr1.get_debit_notes(company_id, return_period_id)
        hsn = await self.gstr1.get_hsn_summary(company_id, return_period_id)
        documents = await self.gstr1.get_document_summary(company_id, return_period_id)

        sections = [
            ExportSection(
                "B2B",
                ["Invoice #", "Date", "Recipient GSTIN", "Recipient", "Place of Supply", "Taxable", "CGST", "SGST", "IGST", "Cess"],
                [[r.invoice_number, r.invoice_date, r.recipient_gstin, r.recipient_name, r.place_of_supply_state_code, r.taxable_value, r.cgst_amount, r.sgst_amount, r.igst_amount, r.cess_amount] for r in b2b],
            ),
            ExportSection(
                "B2C Large",
                ["Invoice #", "Date", "Place of Supply", "Taxable", "IGST"],
                [[r.invoice_number, r.invoice_date, r.place_of_supply_state_code, r.taxable_value, r.igst_amount] for r in b2c_large],
            ),
            ExportSection(
                "B2C Others",
                ["Place of Supply", "Rate", "Invoice Count", "Taxable", "CGST", "SGST", "IGST"],
                [[r.place_of_supply_state_code, r.tax_rate, r.invoice_count, r.taxable_value, r.cgst_amount, r.sgst_amount, r.igst_amount] for r in b2c_others],
            ),
            ExportSection(
                "Exports",
                ["Export Type", "Invoice #", "Date", "Recipient", "Recipient GSTIN", "Shipping Bill #", "Shipping Bill Date", "Port Code", "Taxable", "IGST", "Cess"],
                [[r.export_type, r.invoice_number, r.invoice_date, r.recipient_name, r.recipient_gstin, r.shipping_bill_number, r.shipping_bill_date, r.port_code, r.taxable_value, r.igst_amount, r.cess_amount] for r in exports],
            ),
            ExportSection(
                "Credit Notes",
                ["Note #", "Date", "Against Invoice", "Recipient", "Taxable", "CGST", "SGST", "IGST"],
                [[r.note_number, r.note_date, r.reference_invoice_number, r.recipient_name, r.taxable_value, r.cgst_amount, r.sgst_amount, r.igst_amount] for r in credit_notes],
            ),
            ExportSection(
                "Debit Notes",
                ["Note #", "Date", "Against Invoice", "Recipient", "Taxable", "CGST", "SGST", "IGST"],
                [[r.note_number, r.note_date, r.reference_invoice_number, r.recipient_name, r.taxable_value, r.cgst_amount, r.sgst_amount, r.igst_amount] for r in debit_notes],
            ),
            ExportSection(
                "HSN Summary",
                ["HSN/SAC", "Description", "UQC", "Rate", "Quantity", "Taxable", "Total Value"],
                [[r.hsn_sac, r.description, r.uqc, r.tax_rate, r.quantity, r.taxable_value, r.total_value] for r in hsn],
            ),
            ExportSection(
                "Document Summary",
                ["Document Type", "Total", "Cancelled", "Net"],
                [[r.document_type, r.total_count, r.cancelled_count, r.net_count] for r in documents],
            ),
        ]
        return self._render(
            report_type="GSTR-1 Preparation",
            gstin=gstin,
            period_label=period_label,
            sections=sections,
            fmt=fmt,
            filename_stub=f"gstr1-preparation-{period_label.replace('/', '-')}",
        )

    async def export_gstr3b(self, company_id, return_period_id, fmt: ExportFormat) -> ExportFile:
        gstin, period_label = await self._period_context(company_id, return_period_id)
        summary = await self.gstr3b.generate(company_id, return_period_id)

        sections = [
            ExportSection(
                "Outward Supplies",
                ["Taxable Value", "CGST", "SGST", "IGST", "Cess"],
                [[
                    summary.outward_supplies.taxable_value,
                    summary.outward_supplies.cgst_amount,
                    summary.outward_supplies.sgst_amount,
                    summary.outward_supplies.igst_amount,
                    summary.outward_supplies.cess_amount,
                ]],
            ),
            ExportSection(
                "Input Tax Credit",
                ["Matched ITC", "Approved ITC", "ITC Needing Review", "CGST Available", "SGST Available", "IGST Available", "Cess Available"],
                [[
                    summary.input_tax_credit.itc_matched,
                    summary.input_tax_credit.itc_approved,
                    summary.input_tax_credit.itc_review_required,
                    summary.input_tax_credit.cgst_available,
                    summary.input_tax_credit.sgst_available,
                    summary.input_tax_credit.igst_available,
                    summary.input_tax_credit.cess_available,
                ]],
            ),
            ExportSection(
                "Net Tax Liability",
                ["Output Tax", "Eligible ITC", "Net Liability", "CGST Net", "SGST Net", "IGST Net", "Cess Net"],
                [[
                    summary.net_liability.output_tax,
                    summary.net_liability.eligible_itc,
                    summary.net_liability.net_liability,
                    summary.net_liability.cgst_net,
                    summary.net_liability.sgst_net,
                    summary.net_liability.igst_net,
                    summary.net_liability.cess_net,
                ]],
            ),
        ]
        return self._render(
            report_type="GSTR-3B Preparation",
            gstin=gstin,
            period_label=period_label,
            sections=sections,
            fmt=fmt,
            filename_stub=f"gstr3b-preparation-{period_label.replace('/', '-')}",
        )

    async def export_reconciliation(self, company_id, return_period_id, fmt: ExportFormat) -> ExportFile:
        gstin, period_label = await self._period_context(company_id, return_period_id)
        run = await self.recon_repo.get_latest_run(company_id, return_period_id)
        if run is None:
            raise NotFoundError(
                "No reconciliation has been run for this return period yet",
                code="GST_RECONCILIATION_NOT_FOUND",
            )
        results, _ = await self.recon_repo.list_results_for_run(run.id, limit=100000)

        sections = [
            ExportSection(
                "Summary",
                ["Total Purchases", "Matched", "Partially Matched", "Mismatch", "Books Only", "2B Only", "Duplicate", "Review Required"],
                [[
                    run.total_purchase_invoices, run.matched_count, run.partially_matched_count,
                    run.mismatch_count, run.books_only_count, run.gstr2b_only_count,
                    run.duplicate_count, run.review_required_count,
                ]],
            ),
            ExportSection(
                "Results",
                ["Status", "Books Taxable", "2B Taxable", "Taxable Diff", "Tax Diff", "ITC Category", "ITC Review Status"],
                [[
                    r.status.value, r.books_taxable_value, r.gstr2b_taxable_value, r.taxable_value_diff,
                    r.tax_diff, r.itc_category.value if r.itc_category else None, r.itc_review_status.value,
                ] for r in results],
            ),
        ]
        return self._render(
            report_type="GSTR-2B Reconciliation Report",
            gstin=gstin,
            period_label=period_label,
            sections=sections,
            fmt=fmt,
            filename_stub=f"gstr2b-reconciliation-{period_label.replace('/', '-')}",
        )

    async def export_itc(self, company_id, return_period_id, fmt: ExportFormat) -> ExportFile:
        gstin, period_label = await self._period_context(company_id, return_period_id)
        summary = await self.itc.get_summary(company_id, return_period_id)

        sections = [
            ExportSection(
                "ITC Summary",
                ["Category", "Count", "Taxable Value", "CGST", "SGST", "IGST", "Cess", "Total ITC"],
                [[
                    category.value, entry["count"], entry["taxable_value"], entry["cgst_amount"],
                    entry["sgst_amount"], entry["igst_amount"], entry["cess_amount"], entry["total_itc"],
                ] for category, entry in summary.items()],
            ),
        ]
        return self._render(
            report_type="ITC Summary",
            gstin=gstin,
            period_label=period_label,
            sections=sections,
            fmt=fmt,
            filename_stub=f"itc-summary-{period_label.replace('/', '-')}",
        )
