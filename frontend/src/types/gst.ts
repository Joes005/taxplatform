// Phase 4 — GST Compliance Engine types. Same shape/naming conventions as
// types/accounting.ts (Phase 3): string-literal unions for enums, one
// interface per entity, snake_case matching the backend JSON exactly.

export type GSTRegistrationType = "REGULAR" | "COMPOSITION" | "CASUAL" | "SEZ" | "OTHER";
export type SupplyType = "INTRA_STATE" | "INTER_STATE";
export type GSTTransactionCategory =
  | "B2B"
  | "B2C"
  | "EXPORT"
  | "SEZ"
  | "NIL_RATED"
  | "EXEMPT"
  | "NON_GST"
  | "OTHER"
  | "REVIEW_REQUIRED";
export type GSTReturnPeriodStatus = "OPEN" | "UNDER_REVIEW" | "FINALIZED" | "ARCHIVED";
export type GSTR2BDocumentType = "INVOICE" | "CREDIT_NOTE" | "DEBIT_NOTE";
export type ReconciliationStatus =
  | "MATCHED"
  | "PARTIALLY_MATCHED"
  | "AMOUNT_MISMATCH"
  | "DATE_MISMATCH"
  | "GSTIN_MISMATCH"
  | "INVOICE_NUMBER_MISMATCH"
  | "BOOKS_ONLY"
  | "GSTR2B_ONLY"
  | "DUPLICATE"
  | "REVIEW_REQUIRED";
export type ITCCategory = "MATCHED_ITC" | "UNMATCHED_ITC" | "POTENTIAL_ITC" | "REVIEW_REQUIRED" | "INELIGIBLE";
export type ITCReviewStatus = "PENDING" | "REVIEWED" | "ACCEPTED" | "REJECTED";
export type ValidationSeverity = "INFO" | "WARNING" | "ERROR";

export interface GSTProfile {
  id: string;
  company_id: string;
  gstin: string;
  legal_name: string;
  trade_name: string | null;
  registration_type: GSTRegistrationType;
  state_code: string;
  state_name: string;
  registration_date: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface GSTTaxRate {
  id: string;
  company_id: string | null;
  rate: string;
  description: string | null;
  is_active: boolean;
  effective_from: string;
  effective_to: string | null;
  created_at: string;
  updated_at: string;
}

export interface GSTReturnPeriod {
  id: string;
  company_id: string;
  financial_year_id: string;
  year: number;
  month: number;
  period_start: string;
  period_end: string;
  status: GSTReturnPeriodStatus;
  created_at: string;
  updated_at: string;
}

export interface GSTValidationFinding {
  code: string;
  severity: ValidationSeverity;
  entity: string;
  entity_id: string;
  message: string;
  field: string | null;
}

export interface GSTR1B2BRow {
  sales_invoice_id: string;
  recipient_gstin: string;
  recipient_name: string;
  invoice_number: string;
  invoice_date: string;
  invoice_value: string;
  place_of_supply_state_code: string | null;
  taxable_value: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
}

export interface GSTR1B2CLargeRow {
  sales_invoice_id: string;
  invoice_number: string;
  invoice_date: string;
  invoice_value: string;
  place_of_supply_state_code: string | null;
  taxable_value: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
}

export interface GSTR1B2COthersRow {
  place_of_supply_state_code: string | null;
  tax_rate: string;
  invoice_count: number;
  taxable_value: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
}

export interface GSTR1NoteRow {
  note_id: string;
  note_number: string;
  note_date: string;
  reference_invoice_id: string | null;
  reference_invoice_number: string | null;
  recipient_gstin: string | null;
  recipient_name: string | null;
  taxable_value: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
}

export interface GSTR1HSNRow {
  hsn_sac: string | null;
  description: string | null;
  uqc: string | null;
  tax_rate: string;
  quantity: string;
  taxable_value: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
  total_value: string;
}

export interface GSTR1DocumentSummaryRow {
  document_type: string;
  total_count: number;
  cancelled_count: number;
  net_count: number;
}

export interface GSTR1Overview {
  return_period_id: string;
  b2b_invoice_count: number;
  b2c_large_invoice_count: number;
  b2c_others_invoice_count: number;
  export_count: number;
  credit_note_count: number;
  debit_note_count: number;
  taxable_value: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
  error_count: number;
  warning_count: number;
}

export interface GSTR1ValidationResponse {
  findings: GSTValidationFinding[];
  error_count: number;
  warning_count: number;
}

export interface GSTR2BRecord {
  id: string;
  company_id: string;
  return_period_id: string;
  import_job_id: string | null;
  supplier_gstin: string;
  supplier_name: string | null;
  invoice_number: string;
  invoice_date: string;
  document_type: GSTR2BDocumentType;
  taxable_value: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
  total_tax: string;
  source: string;
  source_reference: string | null;
  created_at: string;
  updated_at: string;
}

export interface GSTReconciliation {
  id: string;
  company_id: string;
  return_period_id: string;
  run_at: string;
  run_by: string;
  total_purchase_invoices: number;
  matched_count: number;
  partially_matched_count: number;
  mismatch_count: number;
  books_only_count: number;
  gstr2b_only_count: number;
  duplicate_count: number;
  review_required_count: number;
  match_percentage: string;
}

export interface GSTReconciliationResult {
  id: string;
  reconciliation_id: string;
  purchase_invoice_id: string | null;
  gstr2b_record_id: string | null;
  status: ReconciliationStatus;
  books_taxable_value: string | null;
  books_cgst_amount: string | null;
  books_sgst_amount: string | null;
  books_igst_amount: string | null;
  books_cess_amount: string | null;
  gstr2b_taxable_value: string | null;
  gstr2b_cgst_amount: string | null;
  gstr2b_sgst_amount: string | null;
  gstr2b_igst_amount: string | null;
  gstr2b_cess_amount: string | null;
  taxable_value_diff: string | null;
  tax_diff: string | null;
  itc_category: ITCCategory | null;
  itc_review_status: ITCReviewStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_comment: string | null;
}

export interface ITCSummaryEntry {
  count: number;
  taxable_value: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
  total_itc: string;
}

export type ITCSummaryResponse = Record<ITCCategory, ITCSummaryEntry>;

export interface GSTR3BOutwardSupplies {
  taxable_value: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
}

export interface GSTR3BInputTaxCredit {
  itc_matched: string;
  itc_approved: string;
  itc_review_required: string;
  cgst_available: string;
  sgst_available: string;
  igst_available: string;
  cess_available: string;
}

export interface GSTR3BNetLiability {
  output_tax: string;
  eligible_itc: string;
  net_liability: string;
  cgst_net: string;
  sgst_net: string;
  igst_net: string;
  cess_net: string;
}

export interface GSTR3BSummary {
  return_period_id: string;
  outward_supplies: GSTR3BOutwardSupplies;
  input_tax_credit: GSTR3BInputTaxCredit;
  net_liability: GSTR3BNetLiability;
  error_count: number;
  warning_count: number;
}
