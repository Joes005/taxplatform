export interface ReportMetadata {
  report_name: string;
  company_id: string;
  company_name: string;
  generated_at: string;
  financial_year?: string | null;
  period_label?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  currency: string;
  is_live: boolean;
  snapshot_version?: string | null;
}

export interface PeriodComparisonValue {
  current: string | number;
  previous: string | number;
  absolute_change: string | number;
  percentage_change: string;
}

// 1. Trial Balance
export interface TrialBalanceLine {
  ledger_id: string;
  ledger_name: string;
  ledger_type: string;
  opening_debit: string | number;
  opening_credit: string | number;
  period_debit: string | number;
  period_credit: string | number;
  closing_debit: string | number;
  closing_credit: string | number;
  net_balance: string | number;
  balance_type: "DEBIT" | "CREDIT";
  drill_down_url: string;
}

export interface TrialBalanceReport {
  metadata: ReportMetadata;
  lines: TrialBalanceLine[];
  total_opening_debit: string | number;
  total_opening_credit: string | number;
  total_period_debit: string | number;
  total_period_credit: string | number;
  total_closing_debit: string | number;
  total_closing_credit: string | number;
  difference: string | number;
  is_balanced: boolean;
  integrity_warning?: string | null;
}

// 2. Profit & Loss
export interface PLLineItem {
  ledger_id?: string | null;
  name: string;
  amount: string | number;
  category: "REVENUE" | "DIRECT_COST" | "OPERATING_EXPENSE" | "OTHER_INCOME" | "OTHER_EXPENSE" | "TAX";
  drill_down_url?: string | null;
}

export interface ProfitLossSection {
  title: string;
  items: PLLineItem[];
  subtotal: string | number;
}

export interface ProfitLossReport {
  metadata: ReportMetadata;
  revenue_section: ProfitLossSection;
  direct_costs_section: ProfitLossSection;
  gross_profit: string | number;
  operating_expenses_section: ProfitLossSection;
  operating_profit: string | number;
  other_income_section: ProfitLossSection;
  other_expenses_section: ProfitLossSection;
  profit_before_tax: string | number;
  tax_expense: string | number;
  net_profit: string | number;
  comparison?: Record<string, PeriodComparisonValue> | null;
  classification_warnings: string[];
}

// 3. Balance Sheet
export interface BalanceSheetItem {
  ledger_id?: string | null;
  name: string;
  amount: string | number;
  category: string;
  drill_down_url?: string | null;
}

export interface BalanceSheetSection {
  title: string;
  items: BalanceSheetItem[];
  subtotal: string | number;
}

export interface BalanceSheetReport {
  metadata: ReportMetadata;
  assets: BalanceSheetSection[];
  total_assets: string | number;
  liabilities: BalanceSheetSection[];
  total_liabilities: string | number;
  equity: BalanceSheetSection[];
  retained_earnings: string | number;
  total_equity: string | number;
  total_liabilities_and_equity: string | number;
  difference: string | number;
  is_balanced: boolean;
  reconciliation_warning?: string | null;
}

// 4. General Ledger
export interface GeneralLedgerEntry {
  id: string;
  date: string;
  voucher_number: string;
  voucher_type: string;
  description?: string | null;
  debit: string | number;
  credit: string | number;
  running_balance: string | number;
  source_reference?: string | null;
  source_id?: string | null;
  drill_down_url?: string | null;
}

export interface GeneralLedgerReport {
  metadata: ReportMetadata;
  ledger_id: string;
  ledger_name: string;
  ledger_type: string;
  opening_balance: string | number;
  opening_balance_type: "DEBIT" | "CREDIT";
  entries: GeneralLedgerEntry[];
  total_debit: string | number;
  total_credit: string | number;
  closing_balance: string | number;
  closing_balance_type: "DEBIT" | "CREDIT";
}

// 5. Receivables & Payables
export interface PartyBalanceRow {
  party_id: string;
  party_name: string;
  party_type: string;
  invoice_count: number;
  gross_invoiced: string | number;
  credit_notes: string | number;
  debit_notes: string | number;
  settled_amount: string | number;
  net_invoiced: string | number;
  outstanding: string | number;
  overdue_amount: string | number;
  drill_down_url: string;
}

export interface ReceivablesPayablesReport {
  metadata: ReportMetadata;
  parties: PartyBalanceRow[];
  total_invoiced: string | number;
  total_credit_notes: string | number;
  total_debit_notes: string | number;
  total_settled: string | number;
  total_outstanding: string | number;
  total_overdue: string | number;
}

// 6. Ageing
export interface AgeingInvoiceRow {
  party_id: string;
  party_name: string;
  party_type: string;
  invoice_id: string;
  invoice_number: string;
  invoice_date: string;
  due_date?: string | null;
  fallback_to_invoice_date: boolean;
  original_amount: string | number;
  outstanding_amount: string | number;
  ageing_days: number;
  bucket: "CURRENT" | "1_30" | "31_60" | "61_90" | "91_180" | "181_PLUS";
  drill_down_url: string;
}

export interface AgeingBucketSummary {
  bucket: string;
  label: string;
  count: number;
  amount: string | number;
}

export interface AgeingReport {
  metadata: ReportMetadata;
  kind: "RECEIVABLES" | "PAYABLES";
  bucket_summaries: AgeingBucketSummary[];
  total_outstanding: string | number;
  invoices: AgeingInvoiceRow[];
}

// 7. Analytics
export interface MonthlyTrendPoint {
  month_name: string;
  month: number;
  year: number;
  gross_amount: string | number;
  net_amount: string | number;
  invoice_count: number;
}

export interface PartyContribution {
  party_id: string;
  party_name: string;
  amount: string | number;
  percentage_of_total: string;
  invoice_count: number;
}

export interface GSTBreakdownItem {
  tax_rate: string | number;
  taxable_amount: string | number;
  cgst: string | number;
  sgst: string | number;
  igst: string | number;
  cess: string | number;
  total_tax: string | number;
}

export interface AnalyticsReport {
  metadata: ReportMetadata;
  kind: "SALES" | "PURCHASE";
  gross_total: string | number;
  credit_notes_total: string | number;
  debit_notes_total: string | number;
  net_total: string | number;
  invoice_count: number;
  party_count: number;
  average_invoice_value: string | number;
  monthly_trends: MonthlyTrendPoint[];
  top_parties: PartyContribution[];
  gst_breakdown: GSTBreakdownItem[];
}

// 8. Cash & Bank
export interface BankAccountBalanceRow {
  account_id: string;
  bank_name: string;
  account_number: string;
  opening_balance: string | number;
  receipts: string | number;
  payments: string | number;
  closing_balance: string | number;
  unreconciled_items_count: number;
  drill_down_url: string;
}

export interface CashBankReport {
  metadata: ReportMetadata;
  accounts: BankAccountBalanceRow[];
  total_opening_balance: string | number;
  total_receipts: string | number;
  total_payments: string | number;
  total_closing_balance: string | number;
  matched_transactions: number;
  unmatched_transactions: number;
  reconciliation_status: string;
}

// 9. GST
export interface GSTPeriodSummary {
  metadata: ReportMetadata;
  outward_taxable: string | number;
  cgst_outward: string | number;
  sgst_outward: string | number;
  igst_outward: string | number;
  cess_outward: string | number;
  total_output_tax: string | number;
  exempt_supplies: string | number;
  nil_rated_supplies: string | number;
  export_supplies: string | number;
  inward_taxable: string | number;
  eligible_itc_cgst: string | number;
  eligible_itc_sgst: string | number;
  eligible_itc_igst: string | number;
  eligible_itc_cess: string | number;
  total_eligible_itc: string | number;
  net_gst_payable: string | number;
  return_status: Record<string, string>;
  reconciliation_mismatch_count: number;
}

// 10. TDS
export interface TDSSectionReportRow {
  section_code: string;
  section_description: string;
  transaction_count: number;
  total_amount: string | number;
  tds_calculated: string | number;
  tds_deducted: string | number;
  tds_paid: string | number;
  tds_payable: string | number;
}

export interface TDSReportSummary {
  metadata: ReportMetadata;
  total_transactions: number;
  total_transaction_amount: string | number;
  total_tds_calculated: string | number;
  total_tds_deducted: string | number;
  total_tds_paid: string | number;
  total_tds_payable: string | number;
  sections: TDSSectionReportRow[];
  total_challans: number;
  challan_deposited_amount: string | number;
  challan_allocated_amount: string | number;
  challan_remaining_amount: string | number;
}

// 11. Income Tax
export interface IncomeHeadSummary {
  head: string;
  gross_income: string | number;
  deductions: string | number;
  net_income: string | number;
}

export interface IncomeTaxReportSummary {
  metadata: ReportMetadata;
  financial_year: string;
  assessment_year: string;
  regime: string;
  heads: IncomeHeadSummary[];
  gross_total_income: string | number;
  total_deductions: string | number;
  total_taxable_income: string | number;
  computed_tax: string | number;
  rebate_87a: string | number;
  surcharge: string | number;
  cess: string | number;
  total_tax_liability: string | number;
  advance_tax_paid: string | number;
  tds_tcs_credit: string | number;
  self_assessment_paid: string | number;
  net_tax_payable_or_refund: string | number;
}

// 12. Audit & Compliance
export interface AuditReportSummary {
  metadata: ReportMetadata;
  total_engagements: number;
  open_engagements: number;
  completed_engagements: number;
  checklist_total: number;
  checklist_completed: number;
  checklist_completion_rate: string;
  total_findings: number;
  open_findings: number;
  critical_findings: number;
  pending_responses: number;
  pending_evidence: number;
  pending_review: number;
  signed_off_count: number;
}

export interface ComplianceReportSummary {
  metadata: ReportMetadata;
  total_obligations: number;
  active_obligations: number;
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  overdue_tasks: number;
  due_soon_tasks: number;
  categories: Array<{ category: string; total: number; completed: number; overdue: number }>;
}

// 13. Management Intelligence Dashboard
export interface ManagementMetricCard {
  key: string;
  label: string;
  current_value: string | number;
  previous_value?: string | number | null;
  change_percentage?: string | null;
  status: "POSITIVE" | "NEUTRAL" | "NEGATIVE";
  drill_down_url: string;
}

export interface ManagementDashboardReport {
  metadata: ReportMetadata;
  cards: ManagementMetricCard[];
  sales_trend: MonthlyTrendPoint[];
  purchase_trend: MonthlyTrendPoint[];
  top_receivables: PartyBalanceRow[];
  top_payables: PartyBalanceRow[];
  audit_findings_count: number;
  overdue_compliance_count: number;
}
