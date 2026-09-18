import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { BankTransaction, BankTransactionReconciliationStatus } from "@/types/bank";

export const bankTransactionService = {
  list: (
    companyId: string,
    page = 1,
    pageSize = 50,
    filters?: { bankAccountId?: string; reconciliationStatus?: BankTransactionReconciliationStatus; search?: string }
  ) =>
    apiClient.get<PaginatedData<BankTransaction>>(
      `/bank/transactions?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (filters?.bankAccountId ? `&bank_account_id=${filters.bankAccountId}` : "") +
        (filters?.reconciliationStatus ? `&reconciliation_status=${filters.reconciliationStatus}` : "") +
        (filters?.search ? `&search=${encodeURIComponent(filters.search)}` : "")
    ),
  get: (companyId: string, transactionId: string) =>
    apiClient.get<BankTransaction>(`/bank/transactions/${transactionId}?company_id=${companyId}`),
  exclude: (companyId: string, transactionId: string) =>
    apiClient.post<BankTransaction>(`/bank/transactions/${transactionId}/exclude?company_id=${companyId}`),
  flagForReview: (companyId: string, transactionId: string) =>
    apiClient.post<BankTransaction>(`/bank/transactions/${transactionId}/review?company_id=${companyId}`),
  createAdjustment: (
    companyId: string,
    transactionId: string,
    payload: { financial_year_id: string; journal_number: string; offset_ledger_id: string; narration?: string }
  ) => apiClient.post(`/bank/transactions/${transactionId}/adjust?company_id=${companyId}`, payload),
};
