import { apiClient } from "@/lib/api-client";
import type { GSTTaxRate } from "@/types/gst";

export interface GSTTaxRatePayload {
  rate: number;
  description?: string | null;
  effective_from: string;
  effective_to?: string | null;
  is_active?: boolean;
}

export const gstTaxRateService = {
  list: (companyId: string) => apiClient.get<GSTTaxRate[]>(`/gst/tax-rates?company_id=${companyId}`),
  create: (companyId: string, payload: GSTTaxRatePayload) =>
    apiClient.post<GSTTaxRate>(`/gst/tax-rates?company_id=${companyId}`, payload),
  update: (companyId: string, rateId: string, payload: Partial<GSTTaxRatePayload>) =>
    apiClient.patch<GSTTaxRate>(`/gst/tax-rates/${rateId}?company_id=${companyId}`, payload),
};
