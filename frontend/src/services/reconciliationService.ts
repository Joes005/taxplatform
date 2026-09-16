import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { GSTReconciliation, GSTReconciliationResult } from "@/types/gst";

export const reconciliationService = {
  run: (companyId: string, periodId: string) =>
    apiClient.post<GSTReconciliation>(
      `/gst/return-periods/${periodId}/reconciliation?company_id=${companyId}`
    ),
  getLatest: (companyId: string, periodId: string) =>
    apiClient.get<GSTReconciliation>(
      `/gst/return-periods/${periodId}/reconciliation?company_id=${companyId}`
    ),
  listResults: (
    companyId: string,
    periodId: string,
    filters?: { status?: string; itcCategory?: string; page?: number; pageSize?: number }
  ) => {
    const params = new URLSearchParams({ company_id: companyId });
    if (filters?.status) params.set("status", filters.status);
    if (filters?.itcCategory) params.set("itc_category", filters.itcCategory);
    params.set("page", String(filters?.page ?? 1));
    params.set("page_size", String(filters?.pageSize ?? 20));
    return apiClient.get<PaginatedData<GSTReconciliationResult>>(
      `/gst/return-periods/${periodId}/reconciliation/results?${params.toString()}`
    );
  },
};
