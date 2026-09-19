import { apiClient } from "@/lib/api-client";
import type { ComplianceCategory, ComplianceFrequency, ComplianceModule, ComplianceRule, CompliancePriority } from "@/types/compliance";

export interface ComplianceRuleCreatePayload {
  code: string;
  name: string;
  description?: string;
  category: ComplianceCategory;
  module: ComplianceModule;
  frequency: ComplianceFrequency;
  due_date_rule: Record<string, unknown>;
  priority?: CompliancePriority;
  effective_from: string;
  effective_to?: string;
  company_specific: boolean;
}

export const complianceRuleService = {
  list: (companyId: string, params?: { category?: ComplianceCategory; module?: ComplianceModule; activeOnly?: boolean }) => {
    const qs = new URLSearchParams({ company_id: companyId });
    if (params?.category) qs.set("category", params.category);
    if (params?.module) qs.set("module", params.module);
    if (params?.activeOnly) qs.set("active_only", "true");
    return apiClient.get<ComplianceRule[]>(`/compliance/rules?${qs.toString()}`);
  },
  create: (companyId: string, payload: ComplianceRuleCreatePayload) =>
    apiClient.post<ComplianceRule>(`/compliance/rules?company_id=${companyId}`, payload),
  activate: (companyId: string, id: string) =>
    apiClient.post<ComplianceRule>(`/compliance/rules/${id}/activate?company_id=${companyId}`),
  deactivate: (companyId: string, id: string) =>
    apiClient.post<ComplianceRule>(`/compliance/rules/${id}/deactivate?company_id=${companyId}`),
};
