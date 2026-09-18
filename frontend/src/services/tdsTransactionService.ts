import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { TDSPayableSummary, TDSTransaction, TDSTransactionStatus } from "@/types/tds";

export interface TDSTransactionPayload {
  deductee_id: string;
  tds_section_id: string;
  transaction_date: string;
  gross_amount: string;
  source_type?: string | null;
  source_id?: string | null;
}

export const tdsTransactionService = {
  list: (
    companyId: string,
    page = 1,
    pageSize = 20,
    filters?: { deducteeId?: string; sectionId?: string; status?: TDSTransactionStatus }
  ) =>
    apiClient.get<PaginatedData<TDSTransaction>>(
      `/tds/transactions?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (filters?.deducteeId ? `&deductee_id=${filters.deducteeId}` : "") +
        (filters?.sectionId ? `&tds_section_id=${filters.sectionId}` : "") +
        (filters?.status ? `&status=${filters.status}` : "")
    ),
  get: (companyId: string, transactionId: string) =>
    apiClient.get<TDSTransaction>(`/tds/transactions/${transactionId}?company_id=${companyId}`),
  create: (companyId: string, payload: TDSTransactionPayload) =>
    apiClient.post<TDSTransaction>(`/tds/transactions?company_id=${companyId}`, payload),
  update: (companyId: string, transactionId: string, payload: Partial<TDSTransactionPayload>) =>
    apiClient.patch<TDSTransaction>(`/tds/transactions/${transactionId}?company_id=${companyId}`, payload),
  calculate: (companyId: string, transactionId: string) =>
    apiClient.post<TDSTransaction>(`/tds/transactions/${transactionId}/calculate?company_id=${companyId}`),
  override: (companyId: string, transactionId: string, tdsAmount: string, overrideReason: string) =>
    apiClient.post<TDSTransaction>(`/tds/transactions/${transactionId}/override?company_id=${companyId}`, {
      tds_amount: tdsAmount,
      override_reason: overrideReason,
    }),
  deduct: (companyId: string, transactionId: string) =>
    apiClient.post<TDSTransaction>(`/tds/transactions/${transactionId}/deduct?company_id=${companyId}`),
  cancel: (companyId: string, transactionId: string) =>
    apiClient.post<TDSTransaction>(`/tds/transactions/${transactionId}/cancel?company_id=${companyId}`),
  payableSummary: (companyId: string, financialYearId?: string) =>
    apiClient.get<TDSPayableSummary>(
      `/tds/transactions/payable-summary?company_id=${companyId}` +
        (financialYearId ? `&financial_year_id=${financialYearId}` : "")
    ),
};
