"""Read-only Income Tax reporting and export (PHASE8 §66-67). Reuses the
same repositories the computation itself uses, and the shared CSV/XLSX
writers already established in Phase 4/5/6/7, rather than a fifth
implementation of file generation.
"""

import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.income_tax_capital_gain_repository import IncomeTaxCapitalGainRepository
from app.repositories.income_tax_deduction_repository import IncomeTaxDeductionRepository
from app.services.income_tax_computation_service import IncomeTaxComputationService
from app.utils.export import ExportFile, ExportFormat, ExportSection, write_csv, write_xlsx


class IncomeTaxReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.computations = IncomeTaxComputationService(db)
        self.deductions = IncomeTaxDeductionRepository(db)
        self.capital_gains = IncomeTaxCapitalGainRepository(db)

    async def export_computation(
        self, company_id: uuid.UUID, computation_id: uuid.UUID, fmt: ExportFormat
    ) -> ExportFile:
        computation = await self.computations.get(company_id, computation_id)
        deductions = await self.deductions.list_for_fy(company_id, computation.financial_year_id)
        capital_gains = await self.capital_gains.list_for_fy(company_id, computation.financial_year_id)

        sections = [
            ExportSection(
                "Income Summary",
                ["Head", "Amount"],
                [
                    ["Salary", computation.salary_income],
                    ["House Property", computation.house_property_income],
                    ["Business/Profession", computation.business_income],
                    ["Capital Gains", computation.capital_gains_income],
                    ["Other Sources", computation.other_income],
                    ["Gross Total Income", computation.gross_total_income],
                ],
            ),
            ExportSection(
                "Deductions",
                ["Section", "Description", "Claimed", "Eligible"],
                [[d.section_code, d.description or "", d.claimed_amount, d.eligible_amount] for d in deductions],
            ),
            ExportSection(
                "Capital Gains Detail",
                ["Asset", "Type", "Sale Date", "Gain"],
                [[g.asset_description, g.gain_type.value, g.sale_date, g.gain_amount] for g in capital_gains],
            ),
            ExportSection(
                "Tax Computation",
                ["Item", "Amount"],
                [
                    ["Taxable Income", computation.taxable_income],
                    ["Tax Before Rebate", computation.tax_before_rebate],
                    ["Rebate", computation.rebate],
                    ["Surcharge", computation.surcharge],
                    ["Cess", computation.cess],
                    ["Gross Tax Liability", computation.gross_tax_liability],
                    ["TDS Credit", computation.tds_credit_total],
                    ["Advance Tax", computation.advance_tax_total],
                    ["Self-Assessment Tax", computation.self_assessment_tax_total],
                    ["Balance Payable / (Refund)", computation.balance_payable_or_refund],
                ],
            ),
        ]

        period_label = f"AY {computation.assessment_year}"
        if fmt == "xlsx":
            content = write_xlsx(
                report_type="Income Tax Computation (Internal Preparation)",
                gstin=computation.tax_regime.value,
                period_label=period_label,
                sections=sections,
            )
            return ExportFile(
                content=content,
                filename=f"income-tax-computation-{computation.assessment_year}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        content = write_csv(
            report_type="Income Tax Computation (Internal Preparation)",
            gstin=computation.tax_regime.value,
            period_label=period_label,
            sections=sections,
        )
        return ExportFile(
            content=content,
            filename=f"income-tax-computation-{computation.assessment_year}.csv",
            media_type="text/csv",
        )
