"""Local CSV/XLSX export of bank reconciliation reports (PHASE6 §45),
reusing the same rendering helpers Phase 4/5 already established rather
than reimplementing CSV/XLSX writing a third time.
"""

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.bank_account_repository import BankAccountRepository
from app.services.bank_reconciliation_service import BankReconciliationService
from app.services.bank_report_service import BankReportService
from app.services.gst_export_service import ExportFile, ExportSection, write_csv, write_xlsx

ExportFormat = Literal["csv", "xlsx"]


class BankExportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.accounts = BankAccountRepository(db)
        self.reconciliations = BankReconciliationService(db)
        self.reports = BankReportService(db)

    async def export_reconciliation(self, company_id, reconciliation_id, fmt: ExportFormat) -> ExportFile:
        reconciliation = await self.reconciliations.get(company_id, reconciliation_id)
        account = await self.accounts.get_by_id_for_company(reconciliation.bank_account_id, company_id)
        if account is None:
            raise NotFoundError("Bank account not found", code="BANK_ACCOUNT_NOT_FOUND")

        unmatched_bank = await self.reports.unmatched_bank_transactions(
            company_id, account.id, period_start=reconciliation.period_start, period_end=reconciliation.period_end
        )
        unmatched_book = (
            await self.reports.unmatched_book_transactions(
                company_id, account.ledger_id, period_start=reconciliation.period_start, period_end=reconciliation.period_end
            )
            if account.ledger_id
            else []
        )
        matches = await self.reports.matching_report(
            company_id, account.id, period_start=reconciliation.period_start, period_end=reconciliation.period_end
        )

        sections = [
            ExportSection(
                "Reconciliation Summary",
                ["Opening Balance", "Closing Balance", "Book Balance", "Bank Balance", "Difference", "Status"],
                [[
                    reconciliation.opening_balance, reconciliation.closing_balance,
                    reconciliation.book_balance, reconciliation.bank_balance,
                    reconciliation.difference, reconciliation.status.value,
                ]],
            ),
            ExportSection(
                "Unmatched Bank Transactions",
                ["Date", "Description", "Reference", "Amount", "Status"],
                [[r.transaction_date, r.description, r.reference_number, r.amount, r.status.value] for r in unmatched_bank],
            ),
            ExportSection(
                "Unmatched Book Transactions",
                ["Source", "Date", "Amount", "Unmatched Amount"],
                [[r.source_label, r.source_date, r.amount, r.unmatched_amount] for r in unmatched_book],
            ),
            ExportSection(
                "Match Details",
                ["Bank Date", "Bank Description", "Source Type", "Matched Amount", "Match Type", "Score"],
                [[
                    m.bank_transaction_date, m.bank_transaction_description, m.source_type.value,
                    m.matched_amount, m.match_type.value, m.match_score,
                ] for m in matches],
            ),
        ]

        period_label = f"{reconciliation.period_start} to {reconciliation.period_end}"
        if fmt == "xlsx":
            content = write_xlsx(
                report_type="Bank Reconciliation Report", gstin=account.account_number_masked,
                period_label=period_label, sections=sections,
            )
            return ExportFile(
                content=content,
                filename=f"bank-reconciliation-{reconciliation.id}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        content = write_csv(
            report_type="Bank Reconciliation Report", gstin=account.account_number_masked,
            period_label=period_label, sections=sections,
        )
        return ExportFile(content=content, filename=f"bank-reconciliation-{reconciliation.id}.csv", media_type="text/csv")
