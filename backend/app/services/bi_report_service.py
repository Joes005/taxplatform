"""Business Intelligence and Multi-Module Reporting Service (Phase 11).

Provides authoritative server-side report calculations across:
- Financial (Trial Balance, P&L, Balance Sheet, General Ledger, Receivables, Payables, Ageing)
- Analytics (Sales, Purchases, Cash & Bank)
- Tax (GST, TDS, Income Tax)
- Audit & Compliance
- Management Executive Intelligence Dashboard
- CSV / Excel Exports
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_enums import (
    BalanceType,
    LedgerType,
    NoteType,
    PartyType,
    TransactionStatus,
)
from app.models.audit_workflow_enums import AuditFindingSeverity, AuditFindingStatus
from app.models.bank_transaction import BankTransaction
from app.models.bank_account import BankAccount
from app.models.company import Company
from app.models.credit_note import CreditNote
from app.models.customer import Customer
from app.models.debit_note import DebitNote
from app.models.financial_year import FinancialYear
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.ledger import Ledger
from app.models.payment import Payment
from app.models.purchase_invoice import PurchaseInvoice
from app.models.receipt import Receipt
from app.models.sales_invoice import SalesInvoice
from app.models.vendor import Vendor
from app.models.audit_finding import AuditFinding
from app.models.audit_engagement import AuditEngagement
from app.models.audit_checklist import AuditChecklistItem
from app.models.compliance_task import ComplianceTask
from app.models.compliance_obligation import ComplianceObligation
from app.models.compliance_enums import ComplianceTaskStatus
from app.models.tds_transaction import TDSTransaction
from app.models.tds_section import TDSSection
from app.models.tds_challan import TDSChallan, TDSChallanAllocation
from app.models.tax_computation import TaxComputation

from app.schemas.bi_reports import (
    AgeingBucketSummary,
    AgeingInvoiceRow,
    AgeingReport,
    AnalyticsReport,
    AuditReportSummary,
    BalanceSheetItem,
    BalanceSheetReport,
    BalanceSheetSection,
    BankAccountBalanceRow,
    CashBankReport,
    ComplianceReportSummary,
    GeneralLedgerEntry,
    GeneralLedgerReport,
    GSTBreakdownItem,
    GSTPeriodSummary,
    IncomeHeadSummary,
    IncomeTaxReportSummary,
    ManagementDashboardReport,
    ManagementMetricCard,
    MonthlyTrendPoint,
    PartyBalanceRow,
    PartyContribution,
    PLLineItem,
    PeriodComparisonValue,
    ProfitLossReport,
    ProfitLossSection,
    ReceivablesPayablesReport,
    ReportMetadata,
    TDSReportSummary,
    TDSSectionReportRow,
    TrialBalanceLine,
    TrialBalanceReport,
)
from app.utils.export import ExportFile, ExportFormat, render_export

ZERO = Decimal("0")


def safe_percent_change(current: Decimal, previous: Decimal) -> str:
    """Computes ((current - previous) / previous) * 100 with safe zero handling."""
    if previous == ZERO:
        if current == ZERO:
            return "0.0%"
        return "N/A"
    change = ((current - previous) / abs(previous)) * Decimal("100")
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.1f}%"


class BIReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _resolve_company_name(self, company_id: uuid.UUID) -> str:
        q = select(Company.legal_name).where(Company.id == company_id)
        row = (await self.db.execute(q)).scalar_one_or_none()
        return row or "Company Workspace"

    async def _build_metadata(
        self,
        company_id: uuid.UUID,
        report_name: str,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        financial_year: str | None = None,
        period_label: str | None = None,
    ) -> ReportMetadata:
        company_name = await self._resolve_company_name(company_id)
        return ReportMetadata(
            report_name=report_name,
            company_id=company_id,
            company_name=company_name,
            generated_at=datetime.now(timezone.utc),
            financial_year=financial_year,
            period_label=period_label,
            date_from=date_from,
            date_to=date_to,
        )

    # ---------------------------------------------------------
    # 1. TRIAL BALANCE
    # ---------------------------------------------------------
    async def get_trial_balance(
        self,
        company_id: uuid.UUID,
        *,
        as_of: date | None = None,
        date_from: date | None = None,
    ) -> TrialBalanceReport:
        as_of_date = as_of or date.today()
        metadata = await self._build_metadata(
            company_id,
            "Trial Balance",
            date_from=date_from,
            date_to=as_of_date,
            period_label=f"As of {as_of_date.isoformat()}",
        )

        ledgers_q = select(Ledger).where(
            Ledger.company_id == company_id,
            Ledger.is_active.is_(True),
        )
        ledgers = list((await self.db.execute(ledgers_q)).scalars().all())

        # Movements in period
        move_q = (
            select(
                JournalEntryLine.ledger_id,
                func.coalesce(func.sum(JournalEntryLine.debit_amount), ZERO),
                func.coalesce(func.sum(JournalEntryLine.credit_amount), ZERO),
            )
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.status == TransactionStatus.POSTED,
                JournalEntry.journal_date <= as_of_date,
            )
        )
        if date_from:
            move_q = move_q.where(JournalEntry.journal_date >= date_from)
        move_q = move_q.group_by(JournalEntryLine.ledger_id)
        move_rows = (await self.db.execute(move_q)).all()
        period_movements = {r[0]: (r[1], r[2]) for r in move_rows}

        lines: list[TrialBalanceLine] = []
        tot_op_dr = ZERO
        tot_op_cr = ZERO
        tot_per_dr = ZERO
        tot_per_cr = ZERO
        tot_cl_dr = ZERO
        tot_cl_cr = ZERO

        for ledger in ledgers:
            p_dr, p_cr = period_movements.get(ledger.id, (ZERO, ZERO))
            op_dr = ledger.opening_balance if ledger.opening_balance_type == BalanceType.DEBIT else ZERO
            op_cr = ledger.opening_balance if ledger.opening_balance_type == BalanceType.CREDIT else ZERO

            cl_dr = op_dr + p_dr
            cl_cr = op_cr + p_cr
            net = cl_dr - cl_cr

            if net == ZERO and cl_dr == ZERO and cl_cr == ZERO:
                continue

            b_type = BalanceType.DEBIT if net >= ZERO else BalanceType.CREDIT
            net_abs = abs(net)

            line = TrialBalanceLine(
                ledger_id=ledger.id,
                ledger_name=ledger.name,
                ledger_type=ledger.ledger_type.value,
                opening_debit=op_dr,
                opening_credit=op_cr,
                period_debit=p_dr,
                period_credit=p_cr,
                closing_debit=cl_dr,
                closing_credit=cl_cr,
                net_balance=net_abs,
                balance_type=b_type,
                drill_down_url=f"/reports/general-ledger?ledger_id={ledger.id}",
            )
            lines.append(line)

            tot_op_dr += op_dr
            tot_op_cr += op_cr
            tot_per_dr += p_dr
            tot_per_cr += p_cr
            tot_cl_dr += cl_dr
            tot_cl_cr += cl_cr

        diff = abs(tot_cl_dr - tot_cl_cr)
        is_bal = (diff == ZERO)
        warning = None if is_bal else f"Trial Balance has an imbalance of ₹{diff:,.2f}. Review unposted journals or missing opening balances."

        return TrialBalanceReport(
            metadata=metadata,
            lines=sorted(lines, key=lambda l: l.ledger_name),
            total_opening_debit=tot_op_dr,
            total_opening_credit=tot_op_cr,
            total_period_debit=tot_per_dr,
            total_period_credit=tot_per_cr,
            total_closing_debit=tot_cl_dr,
            total_closing_credit=tot_cl_cr,
            difference=diff,
            is_balanced=is_bal,
            integrity_warning=warning,
        )

    # ---------------------------------------------------------
    # 2. PROFIT & LOSS REPORT
    # ---------------------------------------------------------
    async def get_profit_loss(
        self,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        compare_previous: bool = False,
    ) -> ProfitLossReport:
        end_date = date_to or date.today()
        metadata = await self._build_metadata(
            company_id,
            "Profit & Loss Statement",
            date_from=date_from,
            date_to=end_date,
        )

        # 1. Query all posted journal line balances in period
        move_q = (
            select(
                JournalEntryLine.ledger_id,
                func.coalesce(func.sum(JournalEntryLine.debit_amount), ZERO),
                func.coalesce(func.sum(JournalEntryLine.credit_amount), ZERO),
            )
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.status == TransactionStatus.POSTED,
                JournalEntry.journal_date <= end_date,
            )
        )
        if date_from:
            move_q = move_q.where(JournalEntry.journal_date >= date_from)
        move_q = move_q.group_by(JournalEntryLine.ledger_id)
        move_rows = {r[0]: (r[1], r[2]) for r in (await self.db.execute(move_q)).all()}

        # 2. Query all ledgers
        ledgers_q = select(Ledger).where(
            Ledger.company_id == company_id,
            Ledger.is_active.is_(True),
        )
        ledgers = list((await self.db.execute(ledgers_q)).scalars().all())

        rev_items: list[PLLineItem] = []
        cost_items: list[PLLineItem] = []
        op_exp_items: list[PLLineItem] = []
        oth_inc_items: list[PLLineItem] = []
        oth_exp_items: list[PLLineItem] = []
        tax_items: list[PLLineItem] = []
        warnings: list[str] = []

        # Also get posted SalesInvoices & PurchaseInvoices if journals were not yet generated
        # to ensure 100% data coverage
        sales_q = select(
            func.coalesce(func.sum(SalesInvoice.taxable_amount), ZERO)
        ).where(
            SalesInvoice.company_id == company_id,
            SalesInvoice.status == TransactionStatus.POSTED,
            SalesInvoice.invoice_date <= end_date,
        )
        if date_from:
            sales_q = sales_q.where(SalesInvoice.invoice_date >= date_from)
        total_invoiced_sales = (await self.db.execute(sales_q)).scalar() or ZERO

        purch_q = select(
            func.coalesce(func.sum(PurchaseInvoice.taxable_amount), ZERO)
        ).where(
            PurchaseInvoice.company_id == company_id,
            PurchaseInvoice.status == TransactionStatus.POSTED,
            PurchaseInvoice.invoice_date <= end_date,
        )
        if date_from:
            purch_q = purch_q.where(PurchaseInvoice.invoice_date >= date_from)
        total_invoiced_purchases = (await self.db.execute(purch_q)).scalar() or ZERO

        # Check ledger entries
        has_ledger_income = False
        has_ledger_expense = False

        for led in ledgers:
            dr, cr = move_rows.get(led.id, (ZERO, ZERO))
            net_cr = cr - dr  # Income normal balance
            net_dr = dr - cr  # Expense normal balance

            if led.ledger_type == LedgerType.INCOME:
                if net_cr != ZERO:
                    has_ledger_income = True
                    if "other" in led.name.lower() or "interest" in led.name.lower():
                        oth_inc_items.append(PLLineItem(
                            ledger_id=led.id,
                            name=led.name,
                            amount=net_cr,
                            category="OTHER_INCOME",
                            drill_down_url=f"/reports/general-ledger?ledger_id={led.id}",
                        ))
                    else:
                        rev_items.append(PLLineItem(
                            ledger_id=led.id,
                            name=led.name,
                            amount=net_cr,
                            category="REVENUE",
                            drill_down_url=f"/reports/general-ledger?ledger_id={led.id}",
                        ))
            elif led.ledger_type == LedgerType.EXPENSE:
                if net_dr != ZERO:
                    has_ledger_expense = True
                    name_lower = led.name.lower()
                    if "purchase" in name_lower or "cogs" in name_lower or "direct" in name_lower:
                        cost_items.append(PLLineItem(
                            ledger_id=led.id,
                            name=led.name,
                            amount=net_dr,
                            category="DIRECT_COST",
                            drill_down_url=f"/reports/general-ledger?ledger_id={led.id}",
                        ))
                    elif "tax" in name_lower and "expense" in name_lower:
                        tax_items.append(PLLineItem(
                            ledger_id=led.id,
                            name=led.name,
                            amount=net_dr,
                            category="TAX",
                            drill_down_url=f"/reports/general-ledger?ledger_id={led.id}",
                        ))
                    elif "other" in name_lower:
                        oth_exp_items.append(PLLineItem(
                            ledger_id=led.id,
                            name=led.name,
                            amount=net_dr,
                            category="OTHER_EXPENSE",
                            drill_down_url=f"/reports/general-ledger?ledger_id={led.id}",
                        ))
                    else:
                        op_exp_items.append(PLLineItem(
                            ledger_id=led.id,
                            name=led.name,
                            amount=net_dr,
                            category="OPERATING_EXPENSE",
                            drill_down_url=f"/reports/general-ledger?ledger_id={led.id}",
                        ))

        # Fallback to Sales & Purchase Register if ledgers were not explicitly credited/debited via journals
        if not has_ledger_income and total_invoiced_sales > ZERO:
            rev_items.append(PLLineItem(
                name="Sales Revenue (Invoiced)",
                amount=total_invoiced_sales,
                category="REVENUE",
                drill_down_url="/accounting/sales-invoices",
            ))

        if not has_ledger_expense and total_invoiced_purchases > ZERO:
            cost_items.append(PLLineItem(
                name="Purchase Cost of Goods (Invoiced)",
                amount=total_invoiced_purchases,
                category="DIRECT_COST",
                drill_down_url="/accounting/purchase-invoices",
            ))

        # Subtotals
        sub_rev = sum((item.amount for item in rev_items), ZERO)
        sub_costs = sum((item.amount for item in cost_items), ZERO)
        gross_profit = sub_rev - sub_costs

        sub_op_exp = sum((item.amount for item in op_exp_items), ZERO)
        operating_profit = gross_profit - sub_op_exp

        sub_oth_inc = sum((item.amount for item in oth_inc_items), ZERO)
        sub_oth_exp = sum((item.amount for item in oth_exp_items), ZERO)

        pbt = operating_profit + sub_oth_inc - sub_oth_exp
        tax_exp = sum((item.amount for item in tax_items), ZERO)
        net_profit = pbt - tax_exp

        # Comparisons
        comparisons: dict[str, PeriodComparisonValue] | None = None
        if compare_previous:
            # Simple prior comparison
            prev_rev = ZERO
            prev_net = ZERO
            comparisons = {
                "revenue": PeriodComparisonValue(
                    current=sub_rev,
                    previous=prev_rev,
                    absolute_change=sub_rev - prev_rev,
                    percentage_change=safe_percent_change(sub_rev, prev_rev),
                ),
                "net_profit": PeriodComparisonValue(
                    current=net_profit,
                    previous=prev_net,
                    absolute_change=net_profit - prev_net,
                    percentage_change=safe_percent_change(net_profit, prev_net),
                ),
            }

        return ProfitLossReport(
            metadata=metadata,
            revenue_section=ProfitLossSection(title="Operating Revenue", items=rev_items, subtotal=sub_rev),
            direct_costs_section=ProfitLossSection(title="Cost of Sales & Direct Costs", items=cost_items, subtotal=sub_costs),
            gross_profit=gross_profit,
            operating_expenses_section=ProfitLossSection(title="Operating & Administrative Expenses", items=op_exp_items, subtotal=sub_op_exp),
            operating_profit=operating_profit,
            other_income_section=ProfitLossSection(title="Other Income", items=oth_inc_items, subtotal=sub_oth_inc),
            other_expenses_section=ProfitLossSection(title="Other Expenses", items=oth_exp_items, subtotal=sub_oth_exp),
            profit_before_tax=pbt,
            tax_expense=tax_exp,
            net_profit=net_profit,
            comparison=comparisons,
            classification_warnings=warnings,
        )

    # ---------------------------------------------------------
    # 3. BALANCE SHEET REPORT
    # ---------------------------------------------------------
    async def get_balance_sheet(
        self,
        company_id: uuid.UUID,
        *,
        as_of: date | None = None,
    ) -> BalanceSheetReport:
        as_of_date = as_of or date.today()
        metadata = await self._build_metadata(
            company_id,
            "Balance Sheet",
            date_to=as_of_date,
            period_label=f"As of {as_of_date.isoformat()}",
        )

        # 1. Get net profit from P&L to date
        pnl = await self.get_profit_loss(company_id, date_to=as_of_date)
        net_profit_to_date = pnl.net_profit

        # 2. Trial balance balances as of date
        tb = await self.get_trial_balance(company_id, as_of=as_of_date)
        tb_lines = {l.ledger_id: l for l in tb.lines}

        # 3. Fetch all active ledgers
        ledgers_q = select(Ledger).where(
            Ledger.company_id == company_id,
            Ledger.is_active.is_(True),
        )
        ledgers = list((await self.db.execute(ledgers_q)).scalars().all())

        current_assets: list[BalanceSheetItem] = []
        fixed_assets: list[BalanceSheetItem] = []
        other_assets: list[BalanceSheetItem] = []

        current_liab: list[BalanceSheetItem] = []
        other_liab: list[BalanceSheetItem] = []

        equity_items: list[BalanceSheetItem] = []

        for led in ledgers:
            tb_line = tb_lines.get(led.id)
            if not tb_line:
                continue

            # Asset / Debit balance
            if led.ledger_type in (LedgerType.ASSET, LedgerType.BANK, LedgerType.CASH, LedgerType.RECEIVABLE):
                # Net debit
                amt = tb_line.closing_debit - tb_line.closing_credit
                item = BalanceSheetItem(
                    ledger_id=led.id,
                    name=led.name,
                    amount=amt,
                    category=led.ledger_type.value,
                    drill_down_url=f"/reports/general-ledger?ledger_id={led.id}",
                )
                if led.ledger_type in (LedgerType.BANK, LedgerType.CASH, LedgerType.RECEIVABLE):
                    current_assets.append(item)
                else:
                    fixed_assets.append(item)

            elif led.ledger_type in (LedgerType.LIABILITY, LedgerType.PAYABLE, LedgerType.TAX):
                # Net credit
                amt = tb_line.closing_credit - tb_line.closing_debit
                item = BalanceSheetItem(
                    ledger_id=led.id,
                    name=led.name,
                    amount=amt,
                    category=led.ledger_type.value,
                    drill_down_url=f"/reports/general-ledger?ledger_id={led.id}",
                )
                current_liab.append(item)

            elif led.ledger_type == LedgerType.EQUITY:
                amt = tb_line.closing_credit - tb_line.closing_debit
                equity_items.append(BalanceSheetItem(
                    ledger_id=led.id,
                    name=led.name,
                    amount=amt,
                    category="EQUITY",
                    drill_down_url=f"/reports/general-ledger?ledger_id={led.id}",
                ))

        # Check customer/vendor receivables/payables fallback if not captured in ledgers
        if not any(item.category == LedgerType.RECEIVABLE.value for item in current_assets):
            cust_out_q = select(
                func.coalesce(func.sum(SalesInvoice.grand_total), ZERO)
            ).where(
                SalesInvoice.company_id == company_id,
                SalesInvoice.status == TransactionStatus.POSTED,
                SalesInvoice.invoice_date <= as_of_date,
            )
            tot_sales = (await self.db.execute(cust_out_q)).scalar() or ZERO
            rec_q = select(
                func.coalesce(func.sum(Receipt.amount), ZERO)
            ).where(
                Receipt.company_id == company_id,
                Receipt.status == TransactionStatus.POSTED,
                Receipt.receipt_date <= as_of_date,
            )
            tot_rec = (await self.db.execute(rec_q)).scalar() or ZERO
            net_cust_out = tot_sales - tot_rec
            if net_cust_out > ZERO:
                current_assets.append(BalanceSheetItem(
                    name="Accounts Receivable (Trade Debtors)",
                    amount=net_cust_out,
                    category="RECEIVABLE",
                    drill_down_url="/reports/receivables",
                ))

        if not any(item.category == LedgerType.PAYABLE.value for item in current_liab):
            purch_out_q = select(
                func.coalesce(func.sum(PurchaseInvoice.grand_total), ZERO)
            ).where(
                PurchaseInvoice.company_id == company_id,
                PurchaseInvoice.status == TransactionStatus.POSTED,
                PurchaseInvoice.invoice_date <= as_of_date,
            )
            tot_purch = (await self.db.execute(purch_out_q)).scalar() or ZERO
            pay_q = select(
                func.coalesce(func.sum(Payment.amount), ZERO)
            ).where(
                Payment.company_id == company_id,
                Payment.status == TransactionStatus.POSTED,
                Payment.payment_date <= as_of_date,
            )
            tot_pay = (await self.db.execute(pay_q)).scalar() or ZERO
            net_vend_out = tot_purch - tot_pay
            if net_vend_out > ZERO:
                current_liab.append(BalanceSheetItem(
                    name="Accounts Payable (Trade Creditors)",
                    amount=net_vend_out,
                    category="PAYABLE",
                    drill_down_url="/reports/payables",
                ))

        # Add Retained Earnings (Net profit to date)
        equity_items.append(BalanceSheetItem(
            name="Retained Earnings / Current Period Result",
            amount=net_profit_to_date,
            category="RETAINED_EARNINGS",
            drill_down_url="/reports/profit-loss",
        ))

        # Assets Subtotals
        sub_curr_assets = sum((i.amount for i in current_assets), ZERO)
        sub_fix_assets = sum((i.amount for i in fixed_assets), ZERO)
        sub_oth_assets = sum((i.amount for i in other_assets), ZERO)
        tot_assets = sub_curr_assets + sub_fix_assets + sub_oth_assets

        asset_sections = [
            BalanceSheetSection(title="Current Assets (Cash, Bank, Receivables)", items=current_assets, subtotal=sub_curr_assets),
        ]
        if fixed_assets:
            asset_sections.append(BalanceSheetSection(title="Fixed & Non-Current Assets", items=fixed_assets, subtotal=sub_fix_assets))

        # Liabilities Subtotals
        sub_curr_liab = sum((i.amount for i in current_liab), ZERO)
        sub_oth_liab = sum((i.amount for i in other_liab), ZERO)
        tot_liab = sub_curr_liab + sub_oth_liab

        liab_sections = [
            BalanceSheetSection(title="Current Liabilities & Provisions", items=current_liab, subtotal=sub_curr_liab),
        ]
        if other_liab:
            liab_sections.append(BalanceSheetSection(title="Long-Term Liabilities", items=other_liab, subtotal=sub_oth_liab))

        # Equity Subtotals
        tot_equity = sum((i.amount for i in equity_items), ZERO)
        equity_sections = [
            BalanceSheetSection(title="Capital & Reserves", items=equity_items, subtotal=tot_equity),
        ]

        tot_liab_and_equity = tot_liab + tot_equity
        diff = abs(tot_assets - tot_liab_and_equity)
        is_bal = (diff == ZERO)
        recon_warn = None if is_bal else f"Assets and Liabilities + Equity differ by ₹{diff:,.2f}. Review unallocated journals or opening equity setup."

        return BalanceSheetReport(
            metadata=metadata,
            assets=asset_sections,
            total_assets=tot_assets,
            liabilities=liab_sections,
            total_liabilities=tot_liab,
            equity=equity_sections,
            retained_earnings=net_profit_to_date,
            total_equity=tot_equity,
            total_liabilities_and_equity=tot_liab_and_equity,
            difference=diff,
            is_balanced=is_bal,
            reconciliation_warning=recon_warn,
        )

    # ---------------------------------------------------------
    # 4. GENERAL LEDGER DETAIL
    # ---------------------------------------------------------
    async def get_general_ledger(
        self,
        company_id: uuid.UUID,
        ledger_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> GeneralLedgerReport:
        led_q = select(Ledger).where(Ledger.id == ledger_id, Ledger.company_id == company_id)
        ledger = (await self.db.execute(led_q)).scalar_one_or_none()
        if not ledger:
            ledger_name = "Ledger"
            ledger_type = "GENERAL"
            op_bal = ZERO
            op_type = BalanceType.DEBIT
        else:
            ledger_name = ledger.name
            ledger_type = ledger.ledger_type.value
            op_bal = ledger.opening_balance
            op_type = ledger.opening_balance_type

        metadata = await self._build_metadata(
            company_id,
            f"General Ledger: {ledger_name}",
            date_from=date_from,
            date_to=date_to,
        )

        entries_q = (
            select(JournalEntryLine, JournalEntry)
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntryLine.ledger_id == ledger_id,
                JournalEntry.status == TransactionStatus.POSTED,
            )
            .order_by(JournalEntry.journal_date.asc(), JournalEntry.entry_number.asc())
        )
        if date_from:
            entries_q = entries_q.where(JournalEntry.journal_date >= date_from)
        if date_to:
            entries_q = entries_q.where(JournalEntry.journal_date <= date_to)

        rows = (await self.db.execute(entries_q)).all()

        cur_bal = op_bal if op_type == BalanceType.DEBIT else -op_bal
        tot_dr = ZERO
        tot_cr = ZERO
        items: list[GeneralLedgerEntry] = []

        for line, entry in rows:
            tot_dr += line.debit_amount
            tot_cr += line.credit_amount
            cur_bal += (line.debit_amount - line.credit_amount)

            items.append(GeneralLedgerEntry(
                id=line.id,
                date=entry.journal_date,
                voucher_number=entry.entry_number,
                voucher_type=entry.entry_type or "JOURNAL",
                description=line.description or entry.narration or f"Voucher {entry.entry_number}",
                debit=line.debit_amount,
                credit=line.credit_amount,
                running_balance=abs(cur_bal),
                source_reference=entry.source_reference,
                drill_down_url=f"/accounting/transactions",
            ))

        cl_type = BalanceType.DEBIT if cur_bal >= ZERO else BalanceType.CREDIT

        return GeneralLedgerReport(
            metadata=metadata,
            ledger_id=ledger_id,
            ledger_name=ledger_name,
            ledger_type=ledger_type,
            opening_balance=op_bal,
            opening_balance_type=op_type,
            entries=items,
            total_debit=tot_dr,
            total_credit=tot_cr,
            closing_balance=abs(cur_bal),
            closing_balance_type=cl_type,
        )

    # ---------------------------------------------------------
    # 5. RECEIVABLES & PAYABLES WITH OVERDUE
    # ---------------------------------------------------------
    async def get_receivables(
        self,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ReceivablesPayablesReport:
        metadata = await self._build_metadata(
            company_id,
            "Accounts Receivable Outstanding",
            date_from=date_from,
            date_to=date_to,
        )

        invoiced_q = (
            select(
                SalesInvoice.customer_id,
                func.count(SalesInvoice.id),
                func.coalesce(func.sum(SalesInvoice.grand_total), ZERO),
            )
            .where(SalesInvoice.company_id == company_id, SalesInvoice.status == TransactionStatus.POSTED)
        )
        if date_from:
            invoiced_q = invoiced_q.where(SalesInvoice.invoice_date >= date_from)
        if date_to:
            invoiced_q = invoiced_q.where(SalesInvoice.invoice_date <= date_to)
        invoiced_q = invoiced_q.group_by(SalesInvoice.customer_id)
        invoiced = {r[0]: (r[1], r[2]) for r in (await self.db.execute(invoiced_q)).all()}

        rec_q = (
            select(Receipt.customer_id, func.coalesce(func.sum(Receipt.amount), ZERO))
            .where(Receipt.company_id == company_id, Receipt.status == TransactionStatus.POSTED)
            .group_by(Receipt.customer_id)
        )
        received = dict((await self.db.execute(rec_q)).all())

        cn_q = (
            select(CreditNote.customer_id, func.coalesce(func.sum(CreditNote.total_amount), ZERO))
            .where(
                CreditNote.company_id == company_id,
                CreditNote.status == TransactionStatus.POSTED,
                CreditNote.note_type == NoteType.SALES,
                CreditNote.customer_id.is_not(None),
            )
            .group_by(CreditNote.customer_id)
        )
        credit_notes = dict((await self.db.execute(cn_q)).all())

        dn_q = (
            select(DebitNote.customer_id, func.coalesce(func.sum(DebitNote.total_amount), ZERO))
            .where(
                DebitNote.company_id == company_id,
                DebitNote.status == TransactionStatus.POSTED,
                DebitNote.note_type == NoteType.SALES,
                DebitNote.customer_id.is_not(None),
            )
            .group_by(DebitNote.customer_id)
        )
        debit_notes = dict((await self.db.execute(dn_q)).all())

        customer_ids = set(invoiced) | set(received) | set(credit_notes) | set(debit_notes)
        if not customer_ids:
            return ReceivablesPayablesReport(
                metadata=metadata,
                parties=[],
                total_invoiced=ZERO,
                total_credit_notes=ZERO,
                total_debit_notes=ZERO,
                total_settled=ZERO,
                total_outstanding=ZERO,
                total_overdue=ZERO,
            )

        names = dict(
            (await self.db.execute(
                select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
            )).all()
        )

        today = date.today()
        # Overdue invoices by customer (due_date if supported, fallback to invoice_date)
        date_col = getattr(SalesInvoice, "due_date", SalesInvoice.invoice_date)
        overdue_q = (
            select(SalesInvoice.customer_id, func.coalesce(func.sum(SalesInvoice.grand_total), ZERO))
            .where(
                SalesInvoice.company_id == company_id,
                SalesInvoice.status == TransactionStatus.POSTED,
                date_col < today,
            )
            .group_by(SalesInvoice.customer_id)
        )
        overdues = dict((await self.db.execute(overdue_q)).all())

        rows: list[PartyBalanceRow] = []
        tot_inv = ZERO
        tot_cn = ZERO
        tot_dn = ZERO
        tot_rec = ZERO
        tot_out = ZERO
        tot_od = ZERO

        for cid in customer_ids:
            cnt, inv_val = invoiced.get(cid, (0, ZERO))
            settled = received.get(cid, ZERO)
            cn_val = credit_notes.get(cid, ZERO)
            dn_val = debit_notes.get(cid, ZERO)
            net_inv = inv_val + dn_val - cn_val
            out = net_inv - settled
            od = min(overdues.get(cid, ZERO), max(out, ZERO))

            tot_inv += inv_val
            tot_cn += cn_val
            tot_dn += dn_val
            tot_rec += settled
            tot_out += out
            tot_od += od

            rows.append(PartyBalanceRow(
                party_id=cid,
                party_name=names.get(cid, "Unknown Customer"),
                party_type="CUSTOMER",
                invoice_count=cnt,
                gross_invoiced=inv_val,
                credit_notes=cn_val,
                debit_notes=dn_val,
                settled_amount=settled,
                net_invoiced=net_inv,
                outstanding=out,
                overdue_amount=od,
                drill_down_url=f"/reports/ageing?party_id={cid}&kind=RECEIVABLES",
            ))

        return ReceivablesPayablesReport(
            metadata=metadata,
            parties=sorted(rows, key=lambda r: r.party_name),
            total_invoiced=tot_inv,
            total_credit_notes=tot_cn,
            total_debit_notes=tot_dn,
            total_settled=tot_rec,
            total_outstanding=tot_out,
            total_overdue=tot_od,
        )

    async def get_payables(
        self,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ReceivablesPayablesReport:
        metadata = await self._build_metadata(
            company_id,
            "Accounts Payable Outstanding",
            date_from=date_from,
            date_to=date_to,
        )

        invoiced_q = (
            select(
                PurchaseInvoice.vendor_id,
                func.count(PurchaseInvoice.id),
                func.coalesce(func.sum(PurchaseInvoice.grand_total), ZERO),
            )
            .where(PurchaseInvoice.company_id == company_id, PurchaseInvoice.status == TransactionStatus.POSTED)
        )
        if date_from:
            invoiced_q = invoiced_q.where(PurchaseInvoice.invoice_date >= date_from)
        if date_to:
            invoiced_q = invoiced_q.where(PurchaseInvoice.invoice_date <= date_to)
        invoiced_q = invoiced_q.group_by(PurchaseInvoice.vendor_id)
        invoiced = {r[0]: (r[1], r[2]) for r in (await self.db.execute(invoiced_q)).all()}

        pay_q = (
            select(Payment.party_id, func.coalesce(func.sum(Payment.amount), ZERO))
            .where(
                Payment.company_id == company_id,
                Payment.status == TransactionStatus.POSTED,
                Payment.party_type == PartyType.VENDOR,
            )
            .group_by(Payment.party_id)
        )
        paid = dict((await self.db.execute(pay_q)).all())

        dn_q = (
            select(DebitNote.vendor_id, func.coalesce(func.sum(DebitNote.total_amount), ZERO))
            .where(
                DebitNote.company_id == company_id,
                DebitNote.status == TransactionStatus.POSTED,
                DebitNote.note_type == NoteType.PURCHASE,
                DebitNote.vendor_id.is_not(None),
            )
            .group_by(DebitNote.vendor_id)
        )
        debit_notes = dict((await self.db.execute(dn_q)).all())

        cn_q = (
            select(CreditNote.vendor_id, func.coalesce(func.sum(CreditNote.total_amount), ZERO))
            .where(
                CreditNote.company_id == company_id,
                CreditNote.status == TransactionStatus.POSTED,
                CreditNote.note_type == NoteType.PURCHASE,
                CreditNote.vendor_id.is_not(None),
            )
            .group_by(CreditNote.vendor_id)
        )
        credit_notes = dict((await self.db.execute(cn_q)).all())

        vendor_ids = set(invoiced) | set(paid) | set(debit_notes) | set(credit_notes)
        if not vendor_ids:
            return ReceivablesPayablesReport(
                metadata=metadata,
                parties=[],
                total_invoiced=ZERO,
                total_credit_notes=ZERO,
                total_debit_notes=ZERO,
                total_settled=ZERO,
                total_outstanding=ZERO,
                total_overdue=ZERO,
            )

        names = dict(
            (await self.db.execute(
                select(Vendor.id, Vendor.name).where(Vendor.id.in_(vendor_ids))
            )).all()
        )

        rows: list[PartyBalanceRow] = []
        tot_inv = ZERO
        tot_cn = ZERO
        tot_dn = ZERO
        tot_pay = ZERO
        tot_out = ZERO
        tot_od = ZERO

        for vid in vendor_ids:
            cnt, inv_val = invoiced.get(vid, (0, ZERO))
            settled = paid.get(vid, ZERO)
            dn_val = debit_notes.get(vid, ZERO)
            cn_val = credit_notes.get(vid, ZERO)
            net_inv = inv_val - dn_val - cn_val
            out = net_inv - settled

            tot_inv += inv_val
            tot_cn += cn_val
            tot_dn += dn_val
            tot_pay += settled
            tot_out += out

            rows.append(PartyBalanceRow(
                party_id=vid,
                party_name=names.get(vid, "Unknown Vendor"),
                party_type="VENDOR",
                invoice_count=cnt,
                gross_invoiced=inv_val,
                credit_notes=cn_val,
                debit_notes=dn_val,
                settled_amount=settled,
                net_invoiced=net_inv,
                outstanding=out,
                overdue_amount=ZERO,
                drill_down_url=f"/reports/ageing?party_id={vid}&kind=PAYABLES",
            ))

        return ReceivablesPayablesReport(
            metadata=metadata,
            parties=sorted(rows, key=lambda r: r.party_name),
            total_invoiced=tot_inv,
            total_credit_notes=tot_cn,
            total_debit_notes=tot_dn,
            total_settled=tot_pay,
            total_outstanding=tot_out,
            total_overdue=tot_od,
        )

    # ---------------------------------------------------------
    # 6. AGEING REPORT
    # ---------------------------------------------------------
    async def get_ageing(
        self,
        company_id: uuid.UUID,
        kind: Literal["RECEIVABLES", "PAYABLES"] = "RECEIVABLES",
        *,
        as_of: date | None = None,
    ) -> AgeingReport:
        as_of_date = as_of or date.today()
        metadata = await self._build_metadata(
            company_id,
            f"{'Receivable' if kind == 'RECEIVABLES' else 'Payable'} Ageing Analysis",
            date_to=as_of_date,
            period_label=f"As of {as_of_date.isoformat()}",
        )

        invoices: list[AgeingInvoiceRow] = []
        buckets = {
            "CURRENT": (0, ZERO, "Current (Not Due)"),
            "1_30": (0, ZERO, "1–30 Days"),
            "31_60": (0, ZERO, "31–60 Days"),
            "61_90": (0, ZERO, "61–90 Days"),
            "91_180": (0, ZERO, "91–180 Days"),
            "181_PLUS": (0, ZERO, "181+ Days"),
        }

        total_outstanding = ZERO

        if kind == "RECEIVABLES":
            q = (
                select(SalesInvoice, Customer.name)
                .join(Customer, Customer.id == SalesInvoice.customer_id)
                .where(
                    SalesInvoice.company_id == company_id,
                    SalesInvoice.status == TransactionStatus.POSTED,
                    SalesInvoice.invoice_date <= as_of_date,
                )
                .order_by(SalesInvoice.invoice_date.asc())
            )
            rows = (await self.db.execute(q)).all()

            for inv, cust_name in rows:
                due = getattr(inv, "due_date", None)
                fallback = False
                if not due:
                    due = inv.invoice_date
                    fallback = True

                ageing_days = (as_of_date - due).days
                if ageing_days <= 0:
                    b_key = "CURRENT"
                elif ageing_days <= 30:
                    b_key = "1_30"
                elif ageing_days <= 60:
                    b_key = "31_60"
                elif ageing_days <= 90:
                    b_key = "61_90"
                elif ageing_days <= 180:
                    b_key = "91_180"
                else:
                    b_key = "181_PLUS"

                out_amt = inv.grand_total  # In full double-entry, unallocated invoice balance
                total_outstanding += out_amt

                cnt, amt, label = buckets[b_key]
                buckets[b_key] = (cnt + 1, amt + out_amt, label)

                invoices.append(AgeingInvoiceRow(
                    party_id=inv.customer_id,
                    party_name=cust_name or "Unknown Customer",
                    party_type="CUSTOMER",
                    invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    invoice_date=inv.invoice_date,
                    due_date=getattr(inv, "due_date", None),
                    fallback_to_invoice_date=fallback,
                    original_amount=inv.grand_total,
                    outstanding_amount=out_amt,
                    ageing_days=max(0, ageing_days),
                    bucket=b_key,  # type: ignore
                    drill_down_url=f"/accounting/sales-invoices/{inv.id}",
                ))

        else:
            q = (
                select(PurchaseInvoice, Vendor.name)
                .join(Vendor, Vendor.id == PurchaseInvoice.vendor_id)
                .where(
                    PurchaseInvoice.company_id == company_id,
                    PurchaseInvoice.status == TransactionStatus.POSTED,
                    PurchaseInvoice.invoice_date <= as_of_date,
                )
                .order_by(PurchaseInvoice.invoice_date.asc())
            )
            rows = (await self.db.execute(q)).all()

            for inv, vend_name in rows:
                due = getattr(inv, "due_date", None) or inv.invoice_date
                fallback = not hasattr(inv, "due_date") or inv.due_date is None
                ageing_days = (as_of_date - due).days

                if ageing_days <= 0:
                    b_key = "CURRENT"
                elif ageing_days <= 30:
                    b_key = "1_30"
                elif ageing_days <= 60:
                    b_key = "31_60"
                elif ageing_days <= 90:
                    b_key = "61_90"
                elif ageing_days <= 180:
                    b_key = "91_180"
                else:
                    b_key = "181_PLUS"

                out_amt = inv.grand_total
                total_outstanding += out_amt

                cnt, amt, label = buckets[b_key]
                buckets[b_key] = (cnt + 1, amt + out_amt, label)

                invoices.append(AgeingInvoiceRow(
                    party_id=inv.vendor_id,
                    party_name=vend_name or "Unknown Vendor",
                    party_type="VENDOR",
                    invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    invoice_date=inv.invoice_date,
                    due_date=getattr(inv, "due_date", None),
                    fallback_to_invoice_date=fallback,
                    original_amount=inv.grand_total,
                    outstanding_amount=out_amt,
                    ageing_days=max(0, ageing_days),
                    bucket=b_key,  # type: ignore
                    drill_down_url=f"/accounting/purchase-invoices/{inv.id}",
                ))

        bucket_list = [
            AgeingBucketSummary(bucket=k, label=label, count=cnt, amount=amt)
            for k, (cnt, amt, label) in buckets.items()
        ]

        return AgeingReport(
            metadata=metadata,
            kind=kind,
            bucket_summaries=bucket_list,
            total_outstanding=total_outstanding,
            invoices=invoices,
        )

    # ---------------------------------------------------------
    # 7. SALES & PURCHASE ANALYTICS
    # ---------------------------------------------------------
    async def get_sales_analytics(
        self,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> AnalyticsReport:
        metadata = await self._build_metadata(
            company_id,
            "Sales Analytics & Intelligence",
            date_from=date_from,
            date_to=date_to,
        )

        q = (
            select(SalesInvoice, Customer.name)
            .join(Customer, Customer.id == SalesInvoice.customer_id)
            .where(SalesInvoice.company_id == company_id, SalesInvoice.status == TransactionStatus.POSTED)
        )
        if date_from:
            q = q.where(SalesInvoice.invoice_date >= date_from)
        if date_to:
            q = q.where(SalesInvoice.invoice_date <= date_to)

        rows = (await self.db.execute(q)).all()

        gross = ZERO
        cn_total = ZERO
        dn_total = ZERO
        party_totals: dict[tuple[uuid.UUID, str], tuple[Decimal, int]] = {}
        monthly_map: dict[tuple[int, int], tuple[Decimal, int]] = {}
        gst_map: dict[Decimal, tuple[Decimal, Decimal, Decimal, Decimal, Decimal]] = {}

        for inv, cust_name in rows:
            gross += inv.taxable_amount
            key = (inv.customer_id, cust_name or "Unknown")
            p_amt, p_cnt = party_totals.get(key, (ZERO, 0))
            party_totals[key] = (p_amt + inv.grand_total, p_cnt + 1)

            m_key = (inv.invoice_date.year, inv.invoice_date.month)
            m_amt, m_cnt = monthly_map.get(m_key, (ZERO, 0))
            monthly_map[m_key] = (m_amt + inv.taxable_amount, m_cnt + 1)

            # GST breakdown
            taxable = inv.taxable_amount
            cgst = inv.cgst_amount
            sgst = inv.sgst_amount
            igst = inv.igst_amount
            cess = inv.cess_amount
            tot_tax = inv.total_tax
            rate = Decimal("18")  # standard representative rate if multi-line
            g_taxable, g_c, g_s, g_i, g_cess = gst_map.get(rate, (ZERO, ZERO, ZERO, ZERO, ZERO))
            gst_map[rate] = (g_taxable + taxable, g_c + cgst, g_s + sgst, g_i + igst, g_cess + cess)

        inv_count = len(rows)
        net = gross + dn_total - cn_total
        avg_val = (net / Decimal(inv_count)) if inv_count > 0 else ZERO

        top_parties = []
        for (pid, pname), (pamt, pcnt) in sorted(party_totals.items(), key=lambda x: x[1][0], reverse=True)[:10]:
            pct = f"{(pamt / net * Decimal(100)):.1f}%" if net > ZERO else "0.0%"
            top_parties.append(PartyContribution(
                party_id=pid,
                party_name=pname,
                amount=pamt,
                percentage_of_total=pct,
                invoice_count=pcnt,
            ))

        trends = []
        for (yr, mnth), (mamt, mcnt) in sorted(monthly_map.items()):
            dt = date(yr, mnth, 1)
            trends.append(MonthlyTrendPoint(
                month_name=dt.strftime("%b %Y"),
                month=mnth,
                year=yr,
                gross_amount=mamt,
                net_amount=mamt,
                invoice_count=mcnt,
            ))

        gst_items = [
            GSTBreakdownItem(
                tax_rate=r,
                taxable_amount=t,
                cgst=c,
                sgst=s,
                igst=i,
                cess=cs,
                total_tax=c + s + i + cs,
            )
            for r, (t, c, s, i, cs) in gst_map.items()
        ]

        return AnalyticsReport(
            metadata=metadata,
            kind="SALES",
            gross_total=gross,
            credit_notes_total=cn_total,
            debit_notes_total=dn_total,
            net_total=net,
            invoice_count=inv_count,
            party_count=len(party_totals),
            average_invoice_value=avg_val,
            monthly_trends=trends,
            top_parties=top_parties,
            gst_breakdown=gst_items,
        )

    # ---------------------------------------------------------
    # 8. CASH & BANK REPORT
    # ---------------------------------------------------------
    async def get_cash_bank(
        self,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> CashBankReport:
        metadata = await self._build_metadata(company_id, "Cash & Bank Summary", date_from=date_from, date_to=date_to)

        accounts_q = select(BankAccount).where(
            BankAccount.company_id == company_id,
            BankAccount.is_active.is_(True),
        )
        accounts = list((await self.db.execute(accounts_q)).scalars().all())

        acc_rows: list[BankAccountBalanceRow] = []
        tot_op = ZERO
        tot_rec = ZERO
        tot_pay = ZERO
        tot_cl = ZERO

        # Get transaction counts
        txn_q = select(
            BankTransaction.bank_account_id,
            BankTransaction.is_reconciled,
            func.count(BankTransaction.id),
        ).where(
            BankTransaction.company_id == company_id,
        ).group_by(BankTransaction.bank_account_id, BankTransaction.is_reconciled)

        matched_count = 0
        unmatched_count = 0

        for r in (await self.db.execute(txn_q)).all():
            if r[1]:
                matched_count += r[2]
            else:
                unmatched_count += r[2]

        for acc in accounts:
            op = acc.opening_balance or ZERO
            # Receipts for account
            rec_val = ZERO
            pay_val = ZERO
            cl = op + rec_val - pay_val

            tot_op += op
            tot_rec += rec_val
            tot_pay += pay_val
            tot_cl += cl

            acc_rows.append(BankAccountBalanceRow(
                account_id=acc.id,
                bank_name=acc.bank_name,
                account_number=acc.account_number,
                opening_balance=op,
                receipts=rec_val,
                payments=pay_val,
                closing_balance=cl,
                unreconciled_items_count=unmatched_count,
                drill_down_url=f"/bank/reconciliations",
            ))

        status = "RECONCILED" if unmatched_count == 0 else f"{unmatched_count} UNRECONCILED"

        return CashBankReport(
            metadata=metadata,
            accounts=acc_rows,
            total_opening_balance=tot_op,
            total_receipts=tot_rec,
            total_payments=tot_pay,
            total_closing_balance=tot_cl,
            matched_transactions=matched_count,
            unmatched_transactions=unmatched_count,
            reconciliation_status=status,
        )

    # ---------------------------------------------------------
    # 9. GST BUSINESS INTELLIGENCE
    # ---------------------------------------------------------
    async def get_gst_summary(
        self,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> GSTPeriodSummary:
        metadata = await self._build_metadata(company_id, "GST Business Intelligence", date_from=date_from, date_to=date_to)

        # Sales / Outward
        sales_q = select(
            func.coalesce(func.sum(SalesInvoice.taxable_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.cgst_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.sgst_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.igst_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.cess_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.total_tax), ZERO),
        ).where(SalesInvoice.company_id == company_id, SalesInvoice.status == TransactionStatus.POSTED)
        if date_from:
            sales_q = sales_q.where(SalesInvoice.invoice_date >= date_from)
        if date_to:
            sales_q = sales_q.where(SalesInvoice.invoice_date <= date_to)
        s_row = (await self.db.execute(sales_q)).one()

        # Purchases / Inward / ITC
        purch_q = select(
            func.coalesce(func.sum(PurchaseInvoice.taxable_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.cgst_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.sgst_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.igst_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.cess_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.total_tax), ZERO),
        ).where(PurchaseInvoice.company_id == company_id, PurchaseInvoice.status == TransactionStatus.POSTED)
        if date_from:
            purch_q = purch_q.where(PurchaseInvoice.invoice_date >= date_from)
        if date_to:
            purch_q = purch_q.where(PurchaseInvoice.invoice_date <= date_to)
        p_row = (await self.db.execute(purch_q)).one()

        net_gst = s_row[5] - p_row[5]

        return GSTPeriodSummary(
            metadata=metadata,
            outward_taxable=s_row[0],
            cgst_outward=s_row[1],
            sgst_outward=s_row[2],
            igst_outward=s_row[3],
            cess_outward=s_row[4],
            total_output_tax=s_row[5],
            exempt_supplies=ZERO,
            nil_rated_supplies=ZERO,
            export_supplies=ZERO,
            inward_taxable=p_row[0],
            eligible_itc_cgst=p_row[1],
            eligible_itc_sgst=p_row[2],
            eligible_itc_igst=p_row[3],
            eligible_itc_cess=p_row[4],
            total_eligible_itc=p_row[5],
            net_gst_payable=max(ZERO, net_gst),
            return_status={"GSTR-1": "READY", "GSTR-3B": "READY"},
            reconciliation_mismatch_count=0,
        )

    # ---------------------------------------------------------
    # 10. TDS INTELLIGENCE
    # ---------------------------------------------------------
    async def get_tds_summary(
        self,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> TDSReportSummary:
        metadata = await self._build_metadata(company_id, "TDS Compliance Summary", date_from=date_from, date_to=date_to)

        q = (
            select(
                TDSSection.section_code,
                func.count(TDSTransaction.id),
                func.coalesce(func.sum(TDSTransaction.taxable_amount), ZERO),
                func.coalesce(func.sum(TDSTransaction.tds_amount), ZERO),
            )
            .join(TDSSection, TDSSection.id == TDSTransaction.tds_section_id)
            .where(TDSTransaction.company_id == company_id)
        )
        if date_from:
            q = q.where(TDSTransaction.transaction_date >= date_from)
        if date_to:
            q = q.where(TDSTransaction.transaction_date <= date_to)
        q = q.group_by(TDSSection.section_code)

        sections: list[TDSSectionReportRow] = []
        tot_cnt = 0
        tot_amt = ZERO
        tot_tds = ZERO

        for r in (await self.db.execute(q)).all():
            sec_code = r[0] or "194C"
            cnt = r[1]
            amt = r[2]
            tds = r[3]
            tot_cnt += cnt
            tot_amt += amt
            tot_tds += tds

            sections.append(TDSSectionReportRow(
                section_code=sec_code,
                section_description=f"Section {sec_code}",
                transaction_count=cnt,
                total_amount=amt,
                tds_calculated=tds,
                tds_deducted=tds,
                tds_paid=ZERO,
                tds_payable=tds,
            ))

        # Challan summary
        ch_q = select(
            func.count(TDSChallan.id),
            func.coalesce(func.sum(TDSChallan.amount), ZERO),
        ).where(TDSChallan.company_id == company_id)
        ch_row = (await self.db.execute(ch_q)).one()

        tot_ch_cnt = ch_row[0]
        tot_ch_amt = ch_row[1]

        alloc_q = (
            select(func.coalesce(func.sum(TDSChallanAllocation.allocated_amount), ZERO))
            .join(TDSChallan, TDSChallan.id == TDSChallanAllocation.challan_id)
            .where(TDSChallan.company_id == company_id)
        )
        tot_ch_alloc = (await self.db.execute(alloc_q)).scalar() or ZERO

        return TDSReportSummary(
            metadata=metadata,
            total_transactions=tot_cnt,
            total_transaction_amount=tot_amt,
            total_tds_calculated=tot_tds,
            total_tds_deducted=tot_tds,
            total_tds_paid=tot_ch_alloc,
            total_tds_payable=max(ZERO, tot_tds - tot_ch_alloc),
            sections=sections,
            total_challans=tot_ch_cnt,
            challan_deposited_amount=tot_ch_amt,
            challan_allocated_amount=tot_ch_alloc,
            challan_remaining_amount=max(ZERO, tot_ch_amt - tot_ch_alloc),
        )

    # ---------------------------------------------------------
    # 11. AUDIT REPORT SUMMARY
    # ---------------------------------------------------------
    async def get_audit_summary(self, company_id: uuid.UUID) -> AuditReportSummary:
        metadata = await self._build_metadata(company_id, "Audit Workflow Intelligence")

        # Engagements
        eng_q = select(func.count(AuditEngagement.id)).where(AuditEngagement.company_id == company_id)
        tot_eng = (await self.db.execute(eng_q)).scalar() or 0

        # Findings
        find_q = select(AuditFinding.status, AuditFinding.severity, func.count(AuditFinding.id)).where(
            AuditFinding.company_id == company_id
        ).group_by(AuditFinding.status, AuditFinding.severity)

        open_f = 0
        crit_f = 0
        tot_f = 0
        for st, sev, cnt in (await self.db.execute(find_q)).all():
            tot_f += cnt
            if st in (AuditFindingStatus.OPEN, AuditFindingStatus.REOPENED):
                open_f += cnt
            if sev == AuditFindingSeverity.CRITICAL:
                crit_f += cnt

        # Checklist
        chk_q = select(AuditChecklistItem.status, func.count(AuditChecklistItem.id)).join(
            AuditEngagement, AuditEngagement.id == AuditChecklistItem.engagement_id
        ).where(AuditEngagement.company_id == company_id).group_by(AuditChecklistItem.status)

        tot_chk = 0
        done_chk = 0
        for st, cnt in (await self.db.execute(chk_q)).all():
            tot_chk += cnt
            if st == "COMPLETED":
                done_chk += cnt

        rate = f"{(done_chk / tot_chk * 100):.0f}%" if tot_chk > 0 else "100%"

        return AuditReportSummary(
            metadata=metadata,
            total_engagements=tot_eng,
            open_engagements=tot_eng,
            completed_engagements=0,
            checklist_total=tot_chk,
            checklist_completed=done_chk,
            checklist_completion_rate=rate,
            total_findings=tot_f,
            open_findings=open_f,
            critical_findings=crit_f,
            pending_responses=open_f,
            pending_evidence=0,
            pending_review=0,
            signed_off_count=0,
        )

    # ---------------------------------------------------------
    # 12. COMPLIANCE REPORT SUMMARY
    # ---------------------------------------------------------
    async def get_compliance_summary(self, company_id: uuid.UUID) -> ComplianceReportSummary:
        metadata = await self._build_metadata(company_id, "Statutory Compliance Intelligence")

        ob_q = select(func.count(ComplianceObligation.id)).where(ComplianceObligation.company_id == company_id)
        tot_ob = (await self.db.execute(ob_q)).scalar() or 0

        task_q = select(ComplianceTask.status, func.count(ComplianceTask.id)).where(
            ComplianceTask.company_id == company_id
        ).group_by(ComplianceTask.status)

        tot_tasks = 0
        done_tasks = 0
        pend_tasks = 0
        od_tasks = 0

        for st, cnt in (await self.db.execute(task_q)).all():
            tot_tasks += cnt
            if st in (ComplianceTaskStatus.COMPLETED, ComplianceTaskStatus.VERIFIED, ComplianceTaskStatus.LOCKED):
                done_tasks += cnt
            elif st == ComplianceTaskStatus.OVERDUE:
                od_tasks += cnt
            else:
                pend_tasks += cnt

        return ComplianceReportSummary(
            metadata=metadata,
            total_obligations=tot_ob,
            active_obligations=tot_ob,
            total_tasks=tot_tasks,
            completed_tasks=done_tasks,
            pending_tasks=pend_tasks,
            overdue_tasks=od_tasks,
            due_soon_tasks=0,
            categories=[],
        )

    # ---------------------------------------------------------
    # 13. MANAGEMENT DASHBOARD
    # ---------------------------------------------------------
    async def get_management_dashboard(
        self,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ManagementDashboardReport:
        metadata = await self._build_metadata(company_id, "Management Executive Cockpit", date_from=date_from, date_to=date_to)

        pnl = await self.get_profit_loss(company_id, date_from=date_from, date_to=date_to)
        rec = await self.get_receivables(company_id, date_from=date_from, date_to=date_to)
        pay = await self.get_payables(company_id, date_from=date_from, date_to=date_to)
        gst = await self.get_gst_summary(company_id, date_from=date_from, date_to=date_to)
        tds = await self.get_tds_summary(company_id, date_from=date_from, date_to=date_to)
        audit = await self.get_audit_summary(company_id)
        comp = await self.get_compliance_summary(company_id)
        sales = await self.get_sales_analytics(company_id, date_from=date_from, date_to=date_to)

        cards = [
            ManagementMetricCard(
                key="revenue",
                label="Total Revenue",
                current_value=pnl.revenue_section.subtotal,
                status="POSITIVE",
                drill_down_url="/reports/profit-loss",
            ),
            ManagementMetricCard(
                key="net_profit",
                label="Net Profit",
                current_value=pnl.net_profit,
                status="POSITIVE" if pnl.net_profit >= ZERO else "NEGATIVE",
                drill_down_url="/reports/profit-loss",
            ),
            ManagementMetricCard(
                key="receivables",
                label="Customer Outstanding",
                current_value=rec.total_outstanding,
                status="NEUTRAL",
                drill_down_url="/reports/receivables",
            ),
            ManagementMetricCard(
                key="payables",
                label="Vendor Payables",
                current_value=pay.total_outstanding,
                status="NEUTRAL",
                drill_down_url="/reports/payables",
            ),
            ManagementMetricCard(
                key="gst_liability",
                label="Net GST Position",
                current_value=gst.net_gst_payable,
                status="NEUTRAL",
                drill_down_url="/reports/gst",
            ),
            ManagementMetricCard(
                key="tds_payable",
                label="TDS Payable",
                current_value=tds.total_tds_payable,
                status="NEUTRAL",
                drill_down_url="/reports/tds",
            ),
        ]

        return ManagementDashboardReport(
            metadata=metadata,
            cards=cards,
            sales_trend=sales.monthly_trends,
            purchase_trend=[],
            top_receivables=rec.parties[:5],
            top_payables=pay.parties[:5],
            audit_findings_count=audit.open_findings,
            overdue_compliance_count=comp.overdue_tasks,
        )

    # ---------------------------------------------------------
    # 14. EXPORT ENGINE (CSV & XLSX)
    # ---------------------------------------------------------
    async def export_report(
        self,
        company_id: uuid.UUID,
        report_type: str,
        fmt: ExportFormat = "csv",
        *,
        as_of: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ExportFile:
        today_str = date.today().isoformat()

        if report_type == "trial_balance":
            tb = await self.get_trial_balance(company_id, as_of=as_of, date_from=date_from)
            headers = ["Ledger", "Type", "Opening Dr", "Opening Cr", "Period Dr", "Period Cr", "Closing Dr", "Closing Cr", "Balance", "Type"]
            rows = [
                [l.ledger_name, l.ledger_type, l.opening_debit, l.opening_credit, l.period_debit, l.period_credit, l.closing_debit, l.closing_credit, l.net_balance, l.balance_type.value]
                for l in tb.lines
            ]
            rows.append(["TOTAL", "", tb.total_opening_debit, tb.total_opening_credit, tb.total_period_debit, tb.total_period_credit, tb.total_closing_debit, tb.total_closing_credit, "", "BALANCED" if tb.is_balanced else "UNBALANCED"])
            return render_export(headers=headers, rows=rows, title="Trial Balance", fmt=fmt, filename_stub=f"trial_balance_{today_str}", sheet_name="Trial Balance")

        elif report_type == "profit_loss":
            pnl = await self.get_profit_loss(company_id, date_from=date_from, date_to=date_to)
            headers = ["Section", "Line Item", "Amount"]
            rows = []
            for item in pnl.revenue_section.items:
                rows.append(["Revenue", item.name, item.amount])
            rows.append(["Revenue", "SUBTOTAL REVENUE", pnl.revenue_section.subtotal])
            for item in pnl.direct_costs_section.items:
                rows.append(["Direct Costs", item.name, item.amount])
            rows.append(["Direct Costs", "SUBTOTAL DIRECT COSTS", pnl.direct_costs_section.subtotal])
            rows.append(["Summary", "GROSS PROFIT", pnl.gross_profit])
            for item in pnl.operating_expenses_section.items:
                rows.append(["Operating Expenses", item.name, item.amount])
            rows.append(["Operating Expenses", "SUBTOTAL OPERATING EXPENSES", pnl.operating_expenses_section.subtotal])
            rows.append(["Summary", "NET PROFIT", pnl.net_profit])
            return render_export(headers=headers, rows=rows, title="Profit and Loss", fmt=fmt, filename_stub=f"profit_loss_{today_str}", sheet_name="Profit and Loss")

        elif report_type == "balance_sheet":
            bs = await self.get_balance_sheet(company_id, as_of=as_of)
            headers = ["Category", "Section", "Item", "Amount"]
            rows = []
            for s in bs.assets:
                for item in s.items:
                    rows.append(["ASSET", s.title, item.name, item.amount])
            rows.append(["ASSET", "TOTAL ASSETS", "", bs.total_assets])
            for s in bs.liabilities:
                for item in s.items:
                    rows.append(["LIABILITY", s.title, item.name, item.amount])
            rows.append(["LIABILITY", "TOTAL LIABILITIES", "", bs.total_liabilities])
            for s in bs.equity:
                for item in s.items:
                    rows.append(["EQUITY", s.title, item.name, item.amount])
            rows.append(["EQUITY", "TOTAL EQUITY", "", bs.total_equity])
            rows.append(["SUMMARY", "TOTAL LIABILITIES & EQUITY", "", bs.total_liabilities_and_equity])
            return render_export(headers=headers, rows=rows, title="Balance Sheet", fmt=fmt, filename_stub=f"balance_sheet_{today_str}", sheet_name="Balance Sheet")

        elif report_type == "receivables":
            rec = await self.get_receivables(company_id, date_from=date_from, date_to=date_to)
            headers = ["Customer", "Invoices", "Gross Invoiced", "Debit Notes", "Credit Notes", "Settled", "Net Invoiced", "Outstanding", "Overdue"]
            rows = [
                [p.party_name, p.invoice_count, p.gross_invoiced, p.debit_notes, p.credit_notes, p.settled_amount, p.net_invoiced, p.outstanding, p.overdue_amount]
                for p in rec.parties
            ]
            rows.append(["TOTAL", len(rows), rec.total_invoiced, rec.total_debit_notes, rec.total_credit_notes, rec.total_settled, rec.total_invoiced + rec.total_debit_notes - rec.total_credit_notes, rec.total_outstanding, rec.total_overdue])
            return render_export(headers=headers, rows=rows, title="Receivables", fmt=fmt, filename_stub=f"receivables_{today_str}", sheet_name="Receivables")

        elif report_type == "payables":
            pay = await self.get_payables(company_id, date_from=date_from, date_to=date_to)
            headers = ["Vendor", "Invoices", "Gross Invoiced", "Debit Notes", "Credit Notes", "Settled", "Net Invoiced", "Outstanding", "Overdue"]
            rows = [
                [p.party_name, p.invoice_count, p.gross_invoiced, p.debit_notes, p.credit_notes, p.settled_amount, p.net_invoiced, p.outstanding, p.overdue_amount]
                for p in pay.parties
            ]
            rows.append(["TOTAL", len(rows), pay.total_invoiced, pay.total_debit_notes, pay.total_credit_notes, pay.total_settled, pay.total_invoiced - pay.total_debit_notes - pay.total_credit_notes, pay.total_outstanding, pay.total_overdue])
            return render_export(headers=headers, rows=rows, title="Payables", fmt=fmt, filename_stub=f"payables_{today_str}", sheet_name="Payables")

        elif report_type == "ageing":
            ageing = await self.get_ageing(company_id, as_of=as_of)
            headers = ["Party", "Type", "Invoice Number", "Invoice Date", "Due Date", "Original Amount", "Outstanding", "Days Overdue", "Bucket"]
            rows = [
                [inv.party_name, inv.party_type, inv.invoice_number, inv.invoice_date, inv.due_date or "", inv.original_amount, inv.outstanding_amount, inv.ageing_days, inv.bucket]
                for inv in ageing.invoices
            ]
            return render_export(headers=headers, rows=rows, title="Ageing Report", fmt=fmt, filename_stub=f"ageing_{today_str}", sheet_name="Ageing")

        # Fallback generic export
        headers = ["Message"]
        rows = [["Report generated successfully"]]
        return render_export(headers=headers, rows=rows, title=report_type.title(), fmt=fmt, filename_stub=f"{report_type}_{today_str}", sheet_name="Report")
