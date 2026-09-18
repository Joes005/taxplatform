import { apiClient } from "@/lib/api-client";
import type { DeductorType, TDSProfile } from "@/types/tds";

export interface TDSProfilePayload {
  tan: string;
  pan: string;
  legal_name: string;
  trade_name?: string | null;
  deductor_type?: DeductorType;
  state_code?: string | null;
  state_name?: string | null;
}

export const tdsProfileService = {
  get: (companyId: string) => apiClient.get<TDSProfile>(`/tds/profile?company_id=${companyId}`),
  create: (companyId: string, payload: TDSProfilePayload) =>
    apiClient.post<TDSProfile>(`/tds/profile?company_id=${companyId}`, payload),
  update: (companyId: string, payload: Partial<TDSProfilePayload>) =>
    apiClient.patch<TDSProfile>(`/tds/profile?company_id=${companyId}`, payload),
};
