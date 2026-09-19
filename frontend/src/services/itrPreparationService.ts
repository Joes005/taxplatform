import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { ITRPreparation, ITRValidationResult } from "@/types/incomeTax";

export const itrPreparationService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<ITRPreparation>>(
      `/income-tax/itr?company_id=${companyId}&page=${page}&page_size=${pageSize}`
    ),
  get: (companyId: string, id: string) =>
    apiClient.get<ITRPreparation>(`/income-tax/itr/${id}?company_id=${companyId}`),
  create: (companyId: string, taxComputationId: string) =>
    apiClient.post<ITRPreparation>(`/income-tax/itr?company_id=${companyId}`, {
      tax_computation_id: taxComputationId,
    }),
  validate: (companyId: string, id: string) =>
    apiClient.post<ITRValidationResult>(`/income-tax/itr/${id}/validate?company_id=${companyId}`),
  submitForReview: (companyId: string, id: string) =>
    apiClient.post<ITRPreparation>(`/income-tax/itr/${id}/submit-review?company_id=${companyId}`),
  approve: (companyId: string, id: string) =>
    apiClient.post<ITRPreparation>(`/income-tax/itr/${id}/approve?company_id=${companyId}`),
  lock: (companyId: string, id: string) =>
    apiClient.post<ITRPreparation>(`/income-tax/itr/${id}/lock?company_id=${companyId}`),
};
