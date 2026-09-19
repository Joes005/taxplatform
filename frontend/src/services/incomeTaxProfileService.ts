import { apiClient } from "@/lib/api-client";
import type { IncomeTaxProfile, IncomeTaxRuleSet, ResidentialStatus, TaxpayerType } from "@/types/incomeTax";

export interface IncomeTaxProfileCreatePayload {
  pan: string;
  legal_name: string;
  trade_name?: string;
  taxpayer_type: TaxpayerType;
  residential_status?: ResidentialStatus;
  business_nature?: string;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
}

export const incomeTaxProfileService = {
  get: (companyId: string) => apiClient.get<IncomeTaxProfile>(`/income-tax/profile?company_id=${companyId}`),
  create: (companyId: string, payload: IncomeTaxProfileCreatePayload) =>
    apiClient.post<IncomeTaxProfile>(`/income-tax/profile?company_id=${companyId}`, payload),
  update: (companyId: string, payload: Partial<IncomeTaxProfileCreatePayload>) =>
    apiClient.patch<IncomeTaxProfile>(`/income-tax/profile?company_id=${companyId}`, payload),
  listRuleSets: (companyId: string, assessmentYear: string) =>
    apiClient.get<IncomeTaxRuleSet[]>(
      `/income-tax/rules?company_id=${companyId}&assessment_year=${assessmentYear}`
    ),
};
