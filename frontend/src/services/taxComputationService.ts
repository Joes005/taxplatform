import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { TaxComputation, TaxComputationSnapshot, TaxRegime } from "@/types/incomeTax";

export const taxComputationService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<TaxComputation>>(
      `/income-tax/computations?company_id=${companyId}&page=${page}&page_size=${pageSize}`
    ),
  get: (companyId: string, id: string) =>
    apiClient.get<TaxComputation>(`/income-tax/computations/${id}?company_id=${companyId}`),
  create: (companyId: string, financialYearId: string, taxRegime: TaxRegime) =>
    apiClient.post<TaxComputation>(`/income-tax/computations?company_id=${companyId}`, {
      financial_year_id: financialYearId,
      tax_regime: taxRegime,
    }),
  calculate: (companyId: string, id: string) =>
    apiClient.post<TaxComputation>(`/income-tax/computations/${id}/calculate?company_id=${companyId}`),
  submitForReview: (companyId: string, id: string) =>
    apiClient.post<TaxComputation>(`/income-tax/computations/${id}/submit-review?company_id=${companyId}`),
  approve: (companyId: string, id: string) =>
    apiClient.post<TaxComputation>(`/income-tax/computations/${id}/approve?company_id=${companyId}`),
  lock: (companyId: string, id: string) =>
    apiClient.post<TaxComputation>(`/income-tax/computations/${id}/lock?company_id=${companyId}`),
  cancel: (companyId: string, id: string) =>
    apiClient.post<TaxComputation>(`/income-tax/computations/${id}/cancel?company_id=${companyId}`),
  listSnapshots: (companyId: string, id: string) =>
    apiClient.get<TaxComputationSnapshot[]>(`/income-tax/computations/${id}/snapshots?company_id=${companyId}`),
  exportComputation: (companyId: string, id: string, format: "csv" | "xlsx") =>
    apiClient.downloadBlob(`/income-tax/reports/computations/${id}/export?company_id=${companyId}&format=${format}`),
};
