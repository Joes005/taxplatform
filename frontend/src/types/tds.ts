// Phase 5 — TDS Compliance Engine types. Same conventions as types/gst.ts:
// string-literal unions for enums, one interface per entity, snake_case
// matching the backend JSON exactly.

export type DeductorType = "COMPANY" | "INDIVIDUAL" | "HUF" | "FIRM" | "LLP" | "GOVERNMENT" | "TRUST" | "OTHER";
export type TDSProfileStatus = "ACTIVE" | "INACTIVE";
export type DeducteeType = "INDIVIDUAL" | "COMPANY" | "FIRM" | "LLP" | "TRUST" | "HUF" | "OTHER";
export type PANStatus = "AVAILABLE" | "NOT_AVAILABLE" | "INVALID" | "PENDING_REVIEW";
export type TDSRateType = "PERCENTAGE" | "FIXED";
export type TDSApplicabilityStatus = "APPLICABLE" | "NOT_APPLICABLE" | "REVIEW_REQUIRED" | "MISSING_DATA";
export type TDSTransactionStatus = "DRAFT" | "CALCULATED" | "DEDUCTED" | "PAID" | "CANCELLED" | "REVIEW_REQUIRED";
export type TDSChallanStatus = "DRAFT" | "GENERATED" | "PAID" | "RECONCILED" | "CANCELLED";
export type TDSReconciliationStatus =
  | "MATCHED"
  | "PARTIALLY_MATCHED"
  | "AMOUNT_MISMATCH"
  | "MISSING_CHALLAN"
  | "UNALLOCATED_PAYMENT"
  | "REVIEW_REQUIRED";
export type TDSReturnPeriodStatus = "OPEN" | "UNDER_REVIEW" | "APPROVED" | "FINALIZED" | "ARCHIVED";
export type TDSQuarter = "Q1" | "Q2" | "Q3" | "Q4";
export type TDSReturnType = "FORM_24Q" | "FORM_26Q" | "FORM_27Q" | "FORM_27EQ";
export type TDSReturnSnapshotStatus = "DRAFT" | "UNDER_REVIEW" | "CHANGES_REQUESTED" | "APPROVED" | "FINALIZED";
export type TDSReviewNoteStatus = "OPEN" | "RESOLVED";

export interface TDSProfile {
  id: string;
  company_id: string;
  tan: string;
  pan: string;
  legal_name: string;
  trade_name: string | null;
  deductor_type: DeductorType;
  state_code: string | null;
  state_name: string | null;
  status: TDSProfileStatus;
  created_at: string;
  updated_at: string;
}

export interface Deductee {
  id: string;
  company_id: string;
  vendor_id: string | null;
  customer_id: string | null;
  name: string;
  code: string | null;
  pan: string | null;
  pan_status: PANStatus;
  deductee_type: DeducteeType;
  email: string | null;
  phone: string | null;
  address: string | null;
  state: string | null;
  state_code: string | null;
  pincode: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TDSSection {
  id: string;
  section_code: string;
  name: string;
  description: string | null;
  payment_nature: string | null;
  is_active: boolean;
  effective_from: string;
  effective_to: string | null;
}

export interface TDSRule {
  id: string;
  tds_section_id: string;
  company_id: string | null;
  rate: string;
  rate_type: TDSRateType;
  no_pan_rate: string | null;
  threshold_amount: string;
  aggregate_threshold_amount: string | null;
  deductee_type: DeducteeType | null;
  pan_required: boolean;
  effective_from: string;
  effective_to: string | null;
  special_condition: string | null;
  is_active: boolean;
}

export interface TDSTransaction {
  id: string;
  company_id: string;
  financial_year_id: string;
  deductee_id: string;
  tds_section_id: string;
  tds_rule_id: string | null;
  source_type: string | null;
  source_id: string | null;
  source: string;
  source_reference: string | null;
  transaction_date: string;
  deduction_date: string | null;
  gross_amount: string;
  taxable_amount: string;
  tds_rate: string;
  tds_amount: string;
  net_amount: string;
  pan_status: PANStatus;
  applicability_status: TDSApplicabilityStatus | null;
  applicability_reason: string | null;
  system_calculated_amount: string | null;
  is_manual_override: boolean;
  override_reason: string | null;
  overridden_by: string | null;
  overridden_at: string | null;
  status: TDSTransactionStatus;
  created_at: string;
  updated_at: string;
}

export interface TDSChallan {
  id: string;
  company_id: string;
  financial_year_id: string;
  challan_number: string;
  challan_date: string;
  amount: string;
  status: TDSChallanStatus;
  bank_reference_number: string | null;
  notes: string | null;
  allocated_amount: string;
  unallocated_amount: string;
  created_at: string;
  updated_at: string;
}

export interface TDSChallanAllocation {
  id: string;
  challan_id: string;
  tds_transaction_id: string;
  allocated_amount: string;
  created_at: string;
}

export interface TDSPaymentReconciliation {
  id: string;
  company_id: string;
  financial_year_id: string;
  tds_transaction_id: string | null;
  tds_challan_id: string | null;
  status: TDSReconciliationStatus;
  expected_amount: string | null;
  allocated_amount: string | null;
  variance_amount: string | null;
  notes: string | null;
  run_at: string;
}

export interface TDSReturnPeriod {
  id: string;
  company_id: string;
  financial_year_id: string;
  quarter: TDSQuarter;
  period_start: string;
  period_end: string;
  status: TDSReturnPeriodStatus;
  created_at: string;
  updated_at: string;
}

export interface TDSReturnSnapshot {
  id: string;
  company_id: string;
  return_period_id: string;
  return_type: TDSReturnType;
  version: number;
  status: TDSReturnSnapshotStatus;
  generated_at: string;
  generated_by: string | null;
  summary_data: TDSReturnPreparationSummary;
}

export interface TDSReviewNote {
  id: string;
  company_id: string;
  return_period_id: string;
  entity_type: string;
  entity_id: string;
  note: string;
  status: TDSReviewNoteStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TDSQuarterlySummary {
  transaction_count: number;
  deductee_count: number;
  gross_amount: string;
  tds_deducted: string;
  tds_paid: string;
  tds_outstanding: string;
  review_required_count: number;
}

export interface TDSSectionSummaryRow {
  tds_section_id: string;
  section_code: string;
  transaction_count: number;
  gross_amount: string;
  tds_deducted: string;
  tds_paid: string;
  tds_outstanding: string;
}

export interface TDSDeducteeSummaryRow {
  deductee_id: string;
  deductee_name: string;
  pan: string | null;
  transaction_count: number;
  gross_amount: string;
  tds_deducted: string;
  tds_paid: string;
  tds_outstanding: string;
}

export interface TDSChallanSummaryRow {
  challan_id: string;
  challan_number: string;
  amount: string;
  allocated_amount: string;
  unallocated_amount: string;
  status: string;
}

export interface TDSReturnPreparationSummary {
  quarterly: TDSQuarterlySummary;
  by_section: TDSSectionSummaryRow[];
  by_deductee: TDSDeducteeSummaryRow[];
  challans: TDSChallanSummaryRow[];
}

export interface TDSPayableSummary {
  tds_deducted: string;
  tds_paid: string;
  tds_outstanding: string;
}
