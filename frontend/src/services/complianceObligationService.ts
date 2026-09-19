import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { ComplianceCategory, ComplianceFrequency, ComplianceModule, ComplianceObligation, ComplianceTask, CompliancePriority } from "@/types/compliance";

export interface ComplianceObligationCreatePayload {
  code: string;
  name: string;
  description?: string;
  category: ComplianceCategory;
  module: ComplianceModule;
  frequency: ComplianceFrequency;
  financial_year_id?: string;
  tax_period?: string;
  start_date: string;
  due_date: string;
  grace_date?: string;
  priority?: CompliancePriority;
}

export const complianceObligationService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<ComplianceObligation>>(
      `/compliance/obligations?company_id=${companyId}&page=${page}&page_size=${pageSize}`
    ),
  create: (companyId: string, payload: ComplianceObligationCreatePayload) =>
    apiClient.post<ComplianceObligation>(`/compliance/obligations?company_id=${companyId}`, payload),
  generateTask: (companyId: string, obligationId: string, title?: string) =>
    apiClient.post<ComplianceTask>(`/compliance/obligations/${obligationId}/generate-task?company_id=${companyId}`, {
      title,
    }),
};
