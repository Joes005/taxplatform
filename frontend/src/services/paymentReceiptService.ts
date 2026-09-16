import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { JournalEntry, Payment, Receipt } from "@/types/accounting";

function qs(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  return search.toString();
}

export interface PaymentPayload {
  financial_year_id: string;
  payment_date: string;
  payment_number: string;
  party_type?: string | null;
  party_id?: string | null;
  ledger_id: string;
  amount: number;
  payment_mode: string;
  reference_number?: string | null;
  notes?: string | null;
}

export const paymentService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<Payment>>(
      `/accounting/payments?${qs({ company_id: companyId, page, page_size: pageSize })}`
    ),
  create: (companyId: string, payload: PaymentPayload) =>
    apiClient.post<Payment>(`/accounting/payments?company_id=${companyId}`, payload),
};

export interface ReceiptPayload {
  financial_year_id: string;
  receipt_date: string;
  receipt_number: string;
  customer_id: string;
  ledger_id: string;
  amount: number;
  payment_mode: string;
  reference_number?: string | null;
  notes?: string | null;
}

export const receiptService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<Receipt>>(
      `/accounting/receipts?${qs({ company_id: companyId, page, page_size: pageSize })}`
    ),
  create: (companyId: string, payload: ReceiptPayload) =>
    apiClient.post<Receipt>(`/accounting/receipts?company_id=${companyId}`, payload),
};

export interface JournalEntryLinePayload {
  ledger_id: string;
  debit_amount?: number;
  credit_amount?: number;
  description?: string | null;
}

export interface JournalEntryPayload {
  financial_year_id: string;
  journal_number: string;
  journal_date: string;
  narration?: string | null;
  lines: JournalEntryLinePayload[];
}

export const journalEntryService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<JournalEntry>>(
      `/accounting/journal-entries?${qs({ company_id: companyId, page, page_size: pageSize })}`
    ),
  create: (companyId: string, payload: JournalEntryPayload) =>
    apiClient.post<JournalEntry>(`/accounting/journal-entries?company_id=${companyId}`, payload),
  post: (companyId: string, id: string) =>
    apiClient.post<JournalEntry>(`/accounting/journal-entries/${id}/post?company_id=${companyId}`),
};
