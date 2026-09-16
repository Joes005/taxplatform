import { apiClient } from "@/lib/api-client";
import type { GSTProfile, GSTRegistrationType } from "@/types/gst";

export interface GSTProfilePayload {
  gstin: string;
  legal_name: string;
  trade_name?: string | null;
  registration_type?: GSTRegistrationType;
  registration_date?: string | null;
}

export const gstProfileService = {
  get: (companyId: string) => apiClient.get<GSTProfile>(`/gst/profile?company_id=${companyId}`),
  create: (companyId: string, payload: GSTProfilePayload) =>
    apiClient.post<GSTProfile>(`/gst/profile?company_id=${companyId}`, payload),
  update: (companyId: string, payload: Partial<GSTProfilePayload> & { is_active?: boolean }) =>
    apiClient.patch<GSTProfile>(`/gst/profile?company_id=${companyId}`, payload),
};
