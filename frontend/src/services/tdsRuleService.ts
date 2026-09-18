import { apiClient } from "@/lib/api-client";
import type { DeducteeType, TDSRateType, TDSRule, TDSSection } from "@/types/tds";

export interface TDSRulePayload {
  tds_section_id: string;
  rate: string;
  rate_type?: TDSRateType;
  no_pan_rate?: string | null;
  threshold_amount?: string;
  aggregate_threshold_amount?: string | null;
  deductee_type?: DeducteeType | null;
  pan_required?: boolean;
  effective_from: string;
  effective_to?: string | null;
  special_condition?: string | null;
  is_active?: boolean;
}

export const tdsSectionService = {
  list: (companyId: string, isActive?: boolean) =>
    apiClient.get<TDSSection[]>(
      `/tds/sections?company_id=${companyId}` + (isActive !== undefined ? `&is_active=${isActive}` : "")
    ),
};

export const tdsRuleService = {
  list: (companyId: string, sectionId?: string) =>
    apiClient.get<TDSRule[]>(
      `/tds/rules?company_id=${companyId}` + (sectionId ? `&tds_section_id=${sectionId}` : "")
    ),
  create: (companyId: string, payload: TDSRulePayload) =>
    apiClient.post<TDSRule>(`/tds/rules?company_id=${companyId}`, payload),
  update: (companyId: string, ruleId: string, payload: Partial<TDSRulePayload>) =>
    apiClient.patch<TDSRule>(`/tds/rules/${ruleId}?company_id=${companyId}`, payload),
};
