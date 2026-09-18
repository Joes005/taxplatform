// Phase 6 — Bank Reconciliation Engine types. Same conventions as
// types/tds.ts: string-literal unions for enums, one interface per
// entity, snake_case matching the backend JSON exactly.

export type BankAccountType = "SAVINGS" | "CURRENT" | "CASH_CREDIT" | "OVERDRAFT" | "OTHER";
export type BankStatementSourceType = "CSV" | "XLSX" | "DOCUMENT" | "MANUAL";
export type BankStatementStatus = "IMPORTED" | "PROCESSING" | "READY" | "RECONCILING" | "RECONCILED" | "FAILED" | "ARCHIVED";
export type BankTransactionType = "DEBIT" | "CREDIT";
export type BankTransactionReconciliationStatus =
  | "UNMATCHED"
  | "MATCH_SUGGESTED"
  | "PARTIALLY_MATCHED"
  | "MATCHED"
  | "MANUALLY_MATCHED"
  | "EXCLUDED"
  | "REVIEW_REQUIRED";
export type BankMatchSourceType = "PAYMENT" | "RECEIPT" | "JOURNAL_ENTRY";
export type BankMatchType = "AUTO" | "MANUAL" | "PARTIAL" | "ADJUSTMENT";
export type BankMatchStatus = "ACTIVE" | "REVERSED";
export type BankReconciliationStatus = "OPEN" | "IN_PROGRESS" | "PENDING_REVIEW" | "RECONCILED" | "LOCKED" | "CANCELLED";
export type BankMatchConfidence = "STRONG_MATCH" | "MATCH_SUGGESTED" | "REVIEW_REQUIRED" | "NO_MATCH";

export interface BankAccount {
  id: string;
  company_id: string;
  ledger_id: string | null;
  bank_name: string;
  branch_name: string | null;
  account_name: string;
  account_number_masked: string;
  account_type: BankAccountType;
  ifsc_code: string | null;
  currency: string;
  opening_balance: string;
  opening_balance_date: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BankStatement {
  id: string;
  company_id: string;
  bank_account_id: string;
  statement_name: string;
  period_start: string;
  period_end: string;
  opening_balance: string;
  closing_balance: string;
  source_type: BankStatementSourceType;
  source_document_id: string | null;
  status: BankStatementStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface BankStatementBalanceCheck {
  opening_balance: string;
  closing_balance: string;
  total_debits: string;
  total_credits: string;
  expected_closing_balance: string;
  difference: string;
  balanced: boolean;
}

export interface BankTransaction {
  id: string;
  company_id: string;
  bank_statement_id: string;
  bank_account_id: string;
  transaction_date: string;
  value_date: string | null;
  description: string;
  reference_number: string | null;
  cheque_number: string | null;
  debit_amount: string;
  credit_amount: string;
  amount: string;
  balance_after_transaction: string | null;
  transaction_type: BankTransactionType;
  normalized_description: string | null;
  normalized_reference: string | null;
  external_transaction_id: string | null;
  reconciliation_status: BankTransactionReconciliationStatus;
  created_at: string;
  updated_at: string;
}

export interface BankMatchCandidate {
  source_type: BankMatchSourceType;
  source_id: string;
  label: string;
  source_date: string;
  source_amount: string;
  counterparty_name: string | null;
  reference_number: string | null;
  score: number;
  confidence: BankMatchConfidence;
}

export interface BankTransactionMatch {
  id: string;
  company_id: string;
  bank_transaction_id: string;
  source_type: BankMatchSourceType;
  source_id: string;
  matched_amount: string;
  match_type: BankMatchType;
  match_score: number | null;
  status: BankMatchStatus;
  matched_by: string;
  matched_at: string;
  notes: string | null;
}

export interface BankReconciliation {
  id: string;
  company_id: string;
  bank_account_id: string;
  period_start: string;
  period_end: string;
  opening_balance: string;
  closing_balance: string;
  book_balance: string | null;
  bank_balance: string | null;
  difference: string | null;
  status: BankReconciliationStatus;
  started_by: string;
  reviewed_by: string | null;
  started_at: string;
  completed_at: string | null;
  reviewed_at: string | null;
}

export interface BankReconciliationSummary {
  reconciliation: BankReconciliation;
  matched_count: number;
  partially_matched_count: number;
  unmatched_count: number;
  review_required_count: number;
  excluded_count: number;
}

export interface UnmatchedBankTransactionRow {
  bank_transaction_id: string;
  transaction_date: string;
  description: string;
  reference_number: string | null;
  amount: string;
  status: BankTransactionReconciliationStatus;
}

export interface UnmatchedBookTransactionRow {
  source_type: BankMatchSourceType;
  source_id: string;
  source_label: string;
  source_date: string;
  amount: string;
  unmatched_amount: string;
}

export interface MatchReportRow {
  match_id: string;
  bank_transaction_id: string;
  bank_transaction_date: string;
  bank_transaction_description: string;
  source_type: BankMatchSourceType;
  source_id: string;
  matched_amount: string;
  match_type: BankMatchType;
  match_score: number | null;
  matched_by: string;
  matched_at: string;
}
