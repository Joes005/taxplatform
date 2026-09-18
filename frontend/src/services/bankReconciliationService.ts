import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { BankReconciliation, BankReconciliationSummary } from "@/types/bank";

export interface BankReconciliationPayload {
  bank_account_id: string;
  period_start: string;
  period_end: string;
  opening_balance: string;
  closing_balance: string;
}

export const bankReconciliationService = {
  list: (companyId: string, page = 1, pageSize = 20, bankAccountId?: string) =>
    apiClient.get<PaginatedData<BankReconciliation>>(
      `/bank/reconciliations?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (bankAccountId ? `&bank_account_id=${bankAccountId}` : "")
    ),
  get: (companyId: string, reconciliationId: string) =>
    apiClient.get<BankReconciliation>(`/bank/reconciliations/${reconciliationId}?company_id=${companyId}`),
  summary: (companyId: string, reconciliationId: string) =>
    apiClient.get<BankReconciliationSummary>(`/bank/reconciliations/${reconciliationId}/summary?company_id=${companyId}`),
  start: (companyId: string, payload: BankReconciliationPayload) =>
    apiClient.post<BankReconciliation>(`/bank/reconciliations?company_id=${companyId}`, payload),
  runMatching: (companyId: string, reconciliationId: string) =>
    apiClient.post<BankReconciliation>(`/bank/reconciliations/${reconciliationId}/run-matching?company_id=${companyId}`),
  submit: (companyId: string, reconciliationId: string) =>
    apiClient.post<BankReconciliation>(`/bank/reconciliations/${reconciliationId}/submit?company_id=${companyId}`, {}),
  approve: (companyId: string, reconciliationId: string, comment?: string) =>
    apiClient.post<BankReconciliation>(`/bank/reconciliations/${reconciliationId}/approve?company_id=${companyId}`, { comment }),
  reject: (companyId: string, reconciliationId: string, comment?: string) =>
    apiClient.post<BankReconciliation>(`/bank/reconciliations/${reconciliationId}/reject?company_id=${companyId}`, { comment }),
  lock: (companyId: string, reconciliationId: string) =>
    apiClient.post<BankReconciliation>(`/bank/reconciliations/${reconciliationId}/lock?company_id=${companyId}`),
  cancel: (companyId: string, reconciliationId: string) =>
    apiClient.post<BankReconciliation>(`/bank/reconciliations/${reconciliationId}/cancel?company_id=${companyId}`),
};
