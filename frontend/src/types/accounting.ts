// Phase 3 — Accounting Data Layer types. Kept in a separate file from
// types/api.ts (Phase 1/2) simply because of the sheer number of new
// entities; the shape and conventions are identical.

export type FinancialYearStatus = "OPEN" | "CLOSED";
export type PeriodStatus = "OPEN" | "CLOSED" | "LOCKED";
export type BalanceType = "DEBIT" | "CREDIT";
export type TransactionStatus = "DRAFT" | "POSTED" | "CANCELLED";
export type DataSource = "MANUAL" | "CSV" | "EXCEL" | "TALLY";
export type LedgerType =
  | "ASSET"
  | "LIABILITY"
  | "EQUITY"
  | "INCOME"
  | "EXPENSE"
  | "RECEIVABLE"
  | "PAYABLE"
  | "BANK"
  | "CASH"
  | "TAX";
export type ItemType = "PRODUCT" | "SERVICE";
export type PaymentMode = "CASH" | "BANK" | "UPI" | "CHEQUE" | "CARD" | "OTHER";
export type PartyType = "CUSTOMER" | "VENDOR" | "OTHER";
export type NoteType = "SALES" | "PURCHASE";
export type OpeningBalanceAccountType = "LEDGER" | "CUSTOMER" | "VENDOR";
export type ImportType =
  | "SALES"
  | "PURCHASES"
  | "CUSTOMERS"
  | "VENDORS"
  | "PRODUCTS"
  | "PAYMENTS"
  | "RECEIPTS"
  | "LEDGERS"
  | "JOURNALS"
  | "TALLY"
  | "GSTR2B"
  | "TDS"
  | "BANK_STATEMENT";
export type ImportStatus =
  | "UPLOADED"
  | "PARSING"
  | "VALIDATING"
  | "READY"
  | "PROCESSING"
  | "COMPLETED"
  | "COMPLETED_WITH_ERRORS"
  | "FAILED"
  | "CANCELLED";

export interface FinancialYear {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  status: FinancialYearStatus;
  created_at: string;
  updated_at: string;
}

export interface AccountingPeriod {
  id: string;
  financial_year_id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: PeriodStatus;
  created_at: string;
  updated_at: string;
}

export interface Ledger {
  id: string;
  name: string;
  code: string | null;
  ledger_type: LedgerType;
  parent_ledger_id: string | null;
  opening_balance: string;
  opening_balance_type: BalanceType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: string;
  name: string;
  code: string | null;
  gstin: string | null;
  pan: string | null;
  email: string | null;
  phone: string | null;
  billing_address: string | null;
  shipping_address: string | null;
  state: string | null;
  state_code: string | null;
  pincode: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Vendor {
  id: string;
  name: string;
  code: string | null;
  gstin: string | null;
  pan: string | null;
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

export interface ProductServiceItem {
  id: string;
  name: string;
  code: string | null;
  item_type: ItemType;
  description: string | null;
  hsn_sac: string | null;
  unit: string | null;
  tax_rate: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InvoiceLineItem {
  id: string;
  product_service_id: string | null;
  description: string | null;
  quantity: string;
  unit?: string | null;
  unit_price: string;
  discount?: string;
  taxable_value: string;
  tax_rate: string;
  cgst_rate: string;
  sgst_rate: string;
  igst_rate: string;
  cess_rate: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
  total_amount: string;
}

export interface SalesInvoice {
  id: string;
  financial_year_id: string;
  customer_id: string;
  invoice_number: string;
  invoice_date: string;
  place_of_supply: string | null;
  place_of_supply_state_code: string | null;
  subtotal: string;
  discount: string;
  taxable_amount: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
  total_tax: string;
  grand_total: string;
  round_off: string;
  status: TransactionStatus;
  source: DataSource;
  source_reference: string | null;
  items: InvoiceLineItem[];
  created_at: string;
  updated_at: string;
}

export interface PurchaseInvoice {
  id: string;
  financial_year_id: string;
  vendor_id: string;
  invoice_number: string;
  invoice_date: string;
  supplier_invoice_number: string | null;
  supplier_invoice_date: string | null;
  place_of_supply: string | null;
  subtotal: string;
  discount: string;
  taxable_amount: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
  total_tax: string;
  grand_total: string;
  status: TransactionStatus;
  source: DataSource;
  source_reference: string | null;
  items: InvoiceLineItem[];
  created_at: string;
  updated_at: string;
}

export interface Payment {
  id: string;
  financial_year_id: string;
  payment_date: string;
  payment_number: string;
  party_type: PartyType | null;
  party_id: string | null;
  ledger_id: string;
  amount: string;
  payment_mode: PaymentMode;
  reference_number: string | null;
  notes: string | null;
  status: TransactionStatus;
  source: DataSource;
  created_at: string;
  updated_at: string;
}

export interface Receipt {
  id: string;
  financial_year_id: string;
  receipt_date: string;
  receipt_number: string;
  customer_id: string;
  ledger_id: string;
  amount: string;
  payment_mode: PaymentMode;
  reference_number: string | null;
  notes: string | null;
  status: TransactionStatus;
  source: DataSource;
  created_at: string;
  updated_at: string;
}

export interface JournalEntryLine {
  id: string;
  ledger_id: string;
  debit_amount: string;
  credit_amount: string;
  description: string | null;
}

export interface JournalEntry {
  id: string;
  financial_year_id: string;
  journal_number: string;
  journal_date: string;
  narration: string | null;
  status: TransactionStatus;
  source: DataSource;
  lines: JournalEntryLine[];
  created_at: string;
  updated_at: string;
}

export interface ImportJob {
  id: string;
  document_id: string;
  financial_year_id: string | null;
  return_period_id: string | null;
  import_type: ImportType;
  status: ImportStatus;
  column_mapping: Record<string, string> | null;
  total_rows: number;
  successful_rows: number;
  failed_rows: number;
  duplicate_rows: number;
  created_at: string;
  completed_at: string | null;
  created_by: string;
}

export interface ImportRow {
  id: string;
  row_number: number;
  raw_data: Record<string, string>;
  normalized_data: Record<string, unknown> | null;
  status: "VALID" | "ERROR" | "DUPLICATE" | "COMMITTED";
  created_record_id: string | null;
}

export interface ImportErrorRow {
  id: string;
  row_number: number;
  field_name: string | null;
  error_code: string;
  error_message: string;
  raw_value: string | null;
  created_at: string;
}

export interface FieldDefinition {
  name: string;
  label: string;
  required: boolean;
}

export interface SalesPurchaseSummary {
  date_from: string | null;
  date_to: string | null;
  invoice_count: number;
  taxable_amount: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  cess_amount: string;
  total_tax: string;
  grand_total: string;
}

export interface PartyOutstanding {
  party_id: string;
  party_name: string;
  invoiced_total: string;
  settled_total: string;
  outstanding: string;
}

export interface LedgerBalance {
  ledger_id: string;
  ledger_name: string;
  ledger_type: string;
  debit: string;
  credit: string;
  balance: string;
  balance_type: BalanceType;
}

export interface TrialBalance {
  as_of: string | null;
  lines: LedgerBalance[];
  total_debit: string;
  total_credit: string;
  is_balanced: boolean;
}
