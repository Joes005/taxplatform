import { apiClient } from "@/lib/api-client";
import type { GSTR3BSummary } from "@/types/gst";

export const gstr3bService = {
  get: (companyId: string, periodId: string) =>
    apiClient.get<GSTR3BSummary>(`/gst/return-periods/${periodId}/gstr3b?company_id=${companyId}`),
};
