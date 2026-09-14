import { apiClient } from "@/lib/api-client";
import type { Company, PaginatedData } from "@/types/api";

export interface CompanyPayload {
  legal_name: string;
  trade_name?: string | null;
  business_type?: string | null;
  pan?: string | null;
  gstin?: string | null;
  tan?: string | null;
  state?: string | null;
  city?: string | null;
  address?: string | null;
  financial_year_start?: string | null;
}

export const companyService = {
  list: (page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<Company>>(`/companies?page=${page}&page_size=${pageSize}`),

  get: (companyId: string) => apiClient.get<Company>(`/companies/${companyId}`),

  create: (payload: CompanyPayload) => apiClient.post<Company>("/companies", payload),

  update: (companyId: string, payload: Partial<CompanyPayload & { is_active: boolean }>) =>
    apiClient.patch<Company>(`/companies/${companyId}`, payload),
};
