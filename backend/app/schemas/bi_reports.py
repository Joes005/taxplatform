"""Pydantic schemas for Phase 11: Reports & Business Intelligence."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.models.accounting_enums import BalanceType


# ---------------------------------------------------------
# Filter & Metadata Schemas
# ---------------------------------------------------------

class ReportMetadata(BaseModel):
    report_name: str
    company_id: uuid.UUID
    company_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    financial_year: str | None = None
    period_label: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    currency: str = "INR"
    is_live: bool = True
    snapshot_version: str | None = None


class PeriodComparisonValue(BaseModel):
    current: Decimal
    previous: Decimal
    absolute_change: Decimal
    percentage_change: str  # e.g. "+12.5%", "-5.0%", or "N/A" (when previous is 0)


# ---------------------------------------------------------
# Trial Balance Schemas
# ---------------------------------------------------------

class TrialBalanceLine(BaseModel):
    ledger_id: uuid.UUID
    ledger_name: str
    ledger_type: str
    opening_debit: Decimal = Decimal("0")
    opening_credit: Decimal = Decimal("0")
    period_debit: Decimal = Decimal("0")
    period_credit: Decimal = Decimal("0")
    closing_debit: Decimal = Decimal("0")
    closing_credit: Decimal = Decimal("0")
    net_balance: Decimal = Decimal("0")
    balance_type: BalanceType
    drill_down_url: str


class TrialBalanceReport(BaseModel):
    metadata: ReportMetadata
    lines: list[TrialBalanceLine]
    total_opening_debit: Decimal = Decimal("0")
    total_opening_credit: Decimal = Decimal("0")
    total_period_debit: Decimal = Decimal("0")
    total_period_credit: Decimal = Decimal("0")
    total_closing_debit: Decimal = Decimal("0")
    total_closing_credit: Decimal = Decimal("0")
    difference: Decimal = Decimal("0")
    is_balanced: bool = True
    integrity_warning: str | None = None


# ---------------------------------------------------------
# Profit & Loss Schemas
# ---------------------------------------------------------

class PLLineItem(BaseModel):
    ledger_id: uuid.UUID | None = None
    name: str
    amount: Decimal
    category: str  # "REVENUE", "DIRECT_COST", "OPERATING_EXPENSE", "OTHER_INCOME", "OTHER_EXPENSE", "TAX"
    drill_down_url: str | None = None


class ProfitLossSection(BaseModel):
    title: str
    items: list[PLLineItem]
    subtotal: Decimal


class ProfitLossReport(BaseModel):
    metadata: ReportMetadata
    revenue_section: ProfitLossSection
    direct_costs_section: ProfitLossSection
    gross_profit: Decimal
    operating_expenses_section: ProfitLossSection
    operating_profit: Decimal
    other_income_section: ProfitLossSection
    other_expenses_section: ProfitLossSection
    profit_before_tax: Decimal
    tax_expense: Decimal
    net_profit: Decimal
    comparison: dict[str, PeriodComparisonValue] | None = None
    classification_warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------
# Balance Sheet Schemas
# ---------------------------------------------------------

class BalanceSheetItem(BaseModel):
    ledger_id: uuid.UUID | None = None
    name: str
    amount: Decimal
    category: str
    drill_down_url: str | None = None


class BalanceSheetSection(BaseModel):
    title: str
    items: list[BalanceSheetItem]
    subtotal: Decimal


class BalanceSheetReport(BaseModel):
    metadata: ReportMetadata
    assets: list[BalanceSheetSection]
    total_assets: Decimal
    liabilities: list[BalanceSheetSection]
    total_liabilities: Decimal
    equity: list[BalanceSheetSection]
    retained_earnings: Decimal
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    difference: Decimal = Decimal("0")
    is_balanced: bool = True
    reconciliation_warning: str | None = None


# ---------------------------------------------------------
# General Ledger Schemas
# ---------------------------------------------------------

class GeneralLedgerEntry(BaseModel):
    id: uuid.UUID
    date: date
    voucher_number: str
    voucher_type: str
    description: str | None = None
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    running_balance: Decimal
    source_reference: str | None = None
    source_id: str | None = None
    drill_down_url: str | None = None


class GeneralLedgerReport(BaseModel):
    metadata: ReportMetadata
    ledger_id: uuid.UUID
    ledger_name: str
    ledger_type: str
    opening_balance: Decimal
    opening_balance_type: BalanceType
    entries: list[GeneralLedgerEntry]
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal
    closing_balance_type: BalanceType


# ---------------------------------------------------------
# Receivables & Payables & Ageing Schemas
# ---------------------------------------------------------

class PartyBalanceRow(BaseModel):
    party_id: uuid.UUID
    party_name: str
    party_type: str
    invoice_count: int
    gross_invoiced: Decimal
    credit_notes: Decimal
    debit_notes: Decimal
    settled_amount: Decimal  # receipts for customer, payments for vendor
    net_invoiced: Decimal
    outstanding: Decimal
    overdue_amount: Decimal
    drill_down_url: str


class ReceivablesPayablesReport(BaseModel):
    metadata: ReportMetadata
    parties: list[PartyBalanceRow]
    total_invoiced: Decimal
    total_credit_notes: Decimal
    total_debit_notes: Decimal
    total_settled: Decimal
    total_outstanding: Decimal
    total_overdue: Decimal


class AgeingInvoiceRow(BaseModel):
    party_id: uuid.UUID
    party_name: str
    party_type: str
    invoice_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    due_date: date | None = None
    fallback_to_invoice_date: bool = False
    original_amount: Decimal
    outstanding_amount: Decimal
    ageing_days: int
    bucket: Literal["CURRENT", "1_30", "31_60", "61_90", "91_180", "181_PLUS"]
    drill_down_url: str


class AgeingBucketSummary(BaseModel):
    bucket: str
    label: str
    count: int
    amount: Decimal


class AgeingReport(BaseModel):
    metadata: ReportMetadata
    kind: Literal["RECEIVABLES", "PAYABLES"]
    bucket_summaries: list[AgeingBucketSummary]
    total_outstanding: Decimal
    invoices: list[AgeingInvoiceRow]


# ---------------------------------------------------------
# Sales & Purchase Analytics Schemas
# ---------------------------------------------------------

class MonthlyTrendPoint(BaseModel):
    month_name: str
    month: int
    year: int
    gross_amount: Decimal
    net_amount: Decimal
    invoice_count: int


class PartyContribution(BaseModel):
    party_id: uuid.UUID
    party_name: str
    amount: Decimal
    percentage_of_total: str
    invoice_count: int


class GSTBreakdownItem(BaseModel):
    tax_rate: Decimal
    taxable_amount: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    cess: Decimal
    total_tax: Decimal


class AnalyticsReport(BaseModel):
    metadata: ReportMetadata
    kind: Literal["SALES", "PURCHASE"]
    gross_total: Decimal
    credit_notes_total: Decimal
    debit_notes_total: Decimal
    net_total: Decimal
    invoice_count: int
    party_count: int
    average_invoice_value: Decimal
    monthly_trends: list[MonthlyTrendPoint]
    top_parties: list[PartyContribution]
    gst_breakdown: list[GSTBreakdownItem]


# ---------------------------------------------------------
# Cash & Bank Report Schemas
# ---------------------------------------------------------

class BankAccountBalanceRow(BaseModel):
    account_id: uuid.UUID
    bank_name: str
    account_number: str
    opening_balance: Decimal
    receipts: Decimal
    payments: Decimal
    closing_balance: Decimal
    unreconciled_items_count: int
    drill_down_url: str


class CashBankReport(BaseModel):
    metadata: ReportMetadata
    accounts: list[BankAccountBalanceRow]
    total_opening_balance: Decimal
    total_receipts: Decimal
    total_payments: Decimal
    total_closing_balance: Decimal
    matched_transactions: int
    unmatched_transactions: int
    reconciliation_status: str


# ---------------------------------------------------------
# GST Business Intelligence Schemas
# ---------------------------------------------------------

class GSTPeriodSummary(BaseModel):
    metadata: ReportMetadata
    outward_taxable: Decimal
    cgst_outward: Decimal
    sgst_outward: Decimal
    igst_outward: Decimal
    cess_outward: Decimal
    total_output_tax: Decimal
    exempt_supplies: Decimal
    nil_rated_supplies: Decimal
    export_supplies: Decimal
    inward_taxable: Decimal
    eligible_itc_cgst: Decimal
    eligible_itc_sgst: Decimal
    eligible_itc_igst: Decimal
    eligible_itc_cess: Decimal
    total_eligible_itc: Decimal
    net_gst_payable: Decimal
    return_status: dict[str, str] = Field(default_factory=dict)
    reconciliation_mismatch_count: int = 0


# ---------------------------------------------------------
# TDS Intelligence Schemas
# ---------------------------------------------------------

class TDSSectionReportRow(BaseModel):
    section_code: str
    section_description: str
    transaction_count: int
    total_amount: Decimal
    tds_calculated: Decimal
    tds_deducted: Decimal
    tds_paid: Decimal
    tds_payable: Decimal


class TDSReportSummary(BaseModel):
    metadata: ReportMetadata
    total_transactions: int
    total_transaction_amount: Decimal
    total_tds_calculated: Decimal
    total_tds_deducted: Decimal
    total_tds_paid: Decimal
    total_tds_payable: Decimal
    sections: list[TDSSectionReportRow]
    total_challans: int
    challan_deposited_amount: Decimal
    challan_allocated_amount: Decimal
    challan_remaining_amount: Decimal


# ---------------------------------------------------------
# Income Tax Intelligence Schemas
# ---------------------------------------------------------

class IncomeHeadSummary(BaseModel):
    head: str
    gross_income: Decimal
    deductions: Decimal
    net_income: Decimal


class IncomeTaxReportSummary(BaseModel):
    metadata: ReportMetadata
    financial_year: str
    assessment_year: str
    regime: str
    heads: list[IncomeHeadSummary]
    gross_total_income: Decimal
    total_deductions: Decimal
    total_taxable_income: Decimal
    computed_tax: Decimal
    rebate_87a: Decimal
    surcharge: Decimal
    cess: Decimal
    total_tax_liability: Decimal
    advance_tax_paid: Decimal
    tds_tcs_credit: Decimal
    self_assessment_paid: Decimal
    net_tax_payable_or_refund: Decimal


# ---------------------------------------------------------
# Audit & Compliance Reports
# ---------------------------------------------------------

class AuditReportSummary(BaseModel):
    metadata: ReportMetadata
    total_engagements: int
    open_engagements: int
    completed_engagements: int
    checklist_total: int
    checklist_completed: int
    checklist_completion_rate: str
    total_findings: int
    open_findings: int
    critical_findings: int
    pending_responses: int
    pending_evidence: int
    pending_review: int
    signed_off_count: int


class ComplianceReportSummary(BaseModel):
    metadata: ReportMetadata
    total_obligations: int
    active_obligations: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    due_soon_tasks: int
    categories: list[dict[str, Any]]


# ---------------------------------------------------------
# Management Intelligence Dashboard
# ---------------------------------------------------------

class ManagementMetricCard(BaseModel):
    key: str
    label: str
    current_value: Decimal
    previous_value: Decimal | None = None
    change_percentage: str | None = None
    status: Literal["POSITIVE", "NEUTRAL", "NEGATIVE"] = "NEUTRAL"
    drill_down_url: str


class ManagementDashboardReport(BaseModel):
    metadata: ReportMetadata
    cards: list[ManagementMetricCard]
    sales_trend: list[MonthlyTrendPoint]
    purchase_trend: list[MonthlyTrendPoint]
    top_receivables: list[PartyBalanceRow]
    top_payables: list[PartyBalanceRow]
    audit_findings_count: int
    overdue_compliance_count: int
