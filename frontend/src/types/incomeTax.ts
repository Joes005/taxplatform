// Phase 8 — Income Tax Compliance Engine types. Same conventions as
// types/tds.ts/types/audit.ts: string-literal unions for enums, one
// interface per entity, snake_case matching the backend JSON exactly.

export type TaxpayerType = "INDIVIDUAL" | "HUF" | "PARTNERSHIP" | "LLP" | "COMPANY" | "TRUST" | "OTHER";
export type ResidentialStatus = "RESIDENT" | "RESIDENT_NOT_ORDINARILY_RESIDENT" | "NON_RESIDENT";
export type TaxRegime = "OLD_REGIME" | "NEW_REGIME";
export type HousePropertyType = "SELF_OCCUPIED" | "LET_OUT";
export type CapitalGainType = "SHORT_TERM" | "LONG_TERM";
export type CapitalAssetType = "EQUITY_SHARES" | "MUTUAL_FUND" | "IMMOVABLE_PROPERTY" | "GOLD_JEWELLERY" | "DEBT_INSTRUMENT" | "OTHER";
export type IncomeTaxSourceType =
  | "SALES_INVOICE" | "PURCHASE_INVOICE" | "PAYMENT" | "RECEIPT" | "JOURNAL_ENTRY" | "LEDGER" | "DOCUMENT"
  | "TDS_TRANSACTION" | "OTHER";
export type TaxAdjustmentType = "ADD_BACK" | "DEDUCTION" | "TIMING_DIFFERENCE" | "DEPRECIATION_ADJUSTMENT" | "OTHER";
export type LedgerTaxClassification = "ALLOWABLE" | "PARTIALLY_ALLOWABLE" | "DISALLOWABLE" | "REVIEW_REQUIRED" | "NOT_CLASSIFIED";
export type TaxLossType = "BUSINESS" | "CAPITAL_SHORT_TERM" | "CAPITAL_LONG_TERM" | "HOUSE_PROPERTY" | "OTHER";
export type TaxComputationStatus =
  | "DRAFT" | "CALCULATED" | "REVIEW_REQUIRED" | "READY_FOR_REVIEW" | "APPROVED" | "LOCKED" | "CANCELLED";
export type ITRFormType = "ITR_1" | "ITR_2" | "ITR_3" | "ITR_5" | "ITR_6" | "ITR_7" | "NOT_DETERMINED";
export type ITRPreparationStatus = "DRAFT" | "IN_PROGRESS" | "VALIDATION_REQUIRED" | "READY_FOR_REVIEW" | "APPROVED" | "LOCKED";
export type ValidationSeverity = "ERROR" | "WARNING" | "REVIEW_REQUIRED";

export interface IncomeTaxProfile {
  id: string;
  company_id: string;
  pan: string;
  legal_name: string;
  trade_name: string | null;
  taxpayer_type: TaxpayerType;
  residential_status: ResidentialStatus;
  date_of_birth_or_incorporation: string | null;
  business_nature: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncomeTaxSlab {
  lower_limit: string;
  upper_limit: string | null;
  rate: string;
  order_index: number;
}
export interface IncomeTaxRebateRule {
  maximum_income: string;
  maximum_rebate: string;
}
export interface IncomeTaxSurchargeRule {
  income_threshold: string;
  rate: string;
  order_index: number;
}
export interface IncomeTaxDeductionRule {
  section_code: string;
  description: string;
  max_amount: string | null;
  allowed_in_old_regime: boolean;
  allowed_in_new_regime: boolean;
}
export interface IncomeTaxRuleSet {
  id: string;
  assessment_year: string;
  taxpayer_type: TaxpayerType;
  tax_regime: TaxRegime;
  effective_from: string;
  effective_to: string | null;
  version: number;
  is_active: boolean;
  cess_rate: string;
  description: string | null;
  slabs: IncomeTaxSlab[];
  rebate_rules: IncomeTaxRebateRule[];
  surcharge_rules: IncomeTaxSurchargeRule[];
  deduction_rules: IncomeTaxDeductionRule[];
}

export interface IncomeTaxSalaryIncome {
  id: string;
  company_id: string;
  financial_year_id: string;
  employer_name: string;
  gross_salary: string;
  allowances: string;
  perquisites: string;
  profit_in_lieu: string;
  standard_deduction: string;
  professional_tax: string;
  tds: string;
  taxable_amount: string;
}

export interface IncomeTaxHousePropertyIncome {
  id: string;
  company_id: string;
  financial_year_id: string;
  property_type: HousePropertyType;
  address: string | null;
  gross_rent: string;
  municipal_tax: string;
  net_annual_value: string;
  standard_deduction: string;
  interest_on_home_loan: string;
  income_or_loss: string;
}

export interface IncomeTaxOtherIncome {
  id: string;
  company_id: string;
  financial_year_id: string;
  income_type: string;
  description: string | null;
  gross_amount: string;
  tds: string;
  net_amount: string;
  source_type: IncomeTaxSourceType | null;
  source_id: string | null;
}

export interface IncomeTaxExemptIncome {
  id: string;
  company_id: string;
  financial_year_id: string;
  section_code: string;
  description: string | null;
  amount: string;
  source_reference: string | null;
}

export interface IncomeTaxCapitalGain {
  id: string;
  company_id: string;
  financial_year_id: string;
  asset_type: CapitalAssetType;
  asset_description: string;
  purchase_date: string;
  sale_date: string;
  purchase_cost: string;
  improvement_cost: string;
  sale_consideration: string;
  transfer_expenses: string;
  indexed_cost: string | null;
  gain_type: CapitalGainType;
  gain_amount: string;
}

export interface IncomeTaxDeduction {
  id: string;
  company_id: string;
  financial_year_id: string;
  section_code: string;
  description: string | null;
  claimed_amount: string;
  eligible_amount: string;
  source_type: IncomeTaxSourceType | null;
  source_id: string | null;
}

export interface IncomeTaxAdjustment {
  id: string;
  company_id: string;
  financial_year_id: string;
  adjustment_type: TaxAdjustmentType;
  description: string;
  book_amount: string;
  tax_amount: string;
  difference: string;
  created_by: string;
}

export interface IncomeTaxLoss {
  id: string;
  company_id: string;
  origin_financial_year_id: string;
  loss_type: TaxLossType;
  amount: string;
  setoff_amount: string;
  carried_forward_amount: string;
  expiry_financial_year_id: string | null;
  created_by: string;
}

export interface IncomeTaxPayment {
  id: string;
  company_id: string;
  financial_year_id: string;
  payment_date: string;
  amount: string;
  challan_number: string | null;
  created_by: string;
}

export interface IncomeTaxCreditEntry {
  id: string;
  company_id: string;
  financial_year_id: string;
  deductor_name: string;
  deductor_tan: string | null;
  section_code: string | null;
  amount: string;
  certificate_reference: string | null;
  source_type: IncomeTaxSourceType | null;
  source_id: string | null;
  created_by: string;
}

export interface BusinessIncomePreview {
  revenue: string;
  purchases: string;
  ledger_income: string;
  ledger_expense_total: string;
  gross_business_income: string;
  eligible_expenses: string;
  disallowances: string;
  other_adjustments: string;
  depreciation_adjustments: string;
  taxable_business_income: string;
  review_required_ledger_ids: string[];
}

export interface TaxComputation {
  id: string;
  company_id: string;
  financial_year_id: string;
  assessment_year: string;
  tax_regime: TaxRegime;
  rule_set_id: string | null;
  status: TaxComputationStatus;
  salary_income: string;
  house_property_income: string;
  business_income: string;
  capital_gains_income: string;
  other_income: string;
  gross_total_income: string;
  total_deductions: string;
  taxable_income: string;
  tax_before_rebate: string;
  rebate: string;
  tax_after_rebate: string;
  surcharge: string;
  cess: string;
  gross_tax_liability: string;
  tds_credit_total: string;
  advance_tax_total: string;
  self_assessment_tax_total: string;
  balance_payable_or_refund: string;
  calculated_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TaxComputationSnapshot {
  id: string;
  tax_computation_id: string;
  rule_set_id: string | null;
  version: number;
  generated_at: string;
  generated_by: string | null;
  summary_data: Record<string, unknown>;
}

export interface ValidationIssue {
  severity: ValidationSeverity;
  code: string;
  message: string;
  field: string | null;
}

export interface ITRPreparation {
  id: string;
  company_id: string;
  tax_computation_id: string;
  itr_form_type: ITRFormType;
  assessment_year: string;
  status: ITRPreparationStatus;
  prepared_by: string;
  reviewed_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ITRValidationResult {
  preparation: ITRPreparation;
  issues: ValidationIssue[];
  has_errors: boolean;
}
