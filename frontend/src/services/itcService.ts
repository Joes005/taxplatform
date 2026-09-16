import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { GSTReconciliationResult, ITCSummaryResponse } from "@/types/gst";

export const itcService = {
  summary: (companyId: string, periodId: string) =>
    apiClient.get<ITCSummaryResponse>(`/gst/return-periods/${periodId}/itc/summary?company_id=${companyId}`),
  list: (
    companyId: string,
    periodId: string,
    filters?: { category?: string; reviewStatus?: string; page?: number; pageSize?: number }
  ) => {
    const params = new URLSearchParams({ company_id: companyId });
    if (filters?.category) params.set("category", filters.category);
    if (filters?.reviewStatus) params.set("review_status", filters.reviewStatus);
    params.set("page", String(filters?.page ?? 1));
    params.set("page_size", String(filters?.pageSize ?? 20));
    return apiClient.get<PaginatedData<GSTReconciliationResult>>(
      `/gst/return-periods/${periodId}/itc?${params.toString()}`
    );
  },
  review: (companyId: string, periodId: string, resultId: string, comment?: string) =>
    apiClient.post<GSTReconciliationResult>(
      `/gst/return-periods/${periodId}/itc/${resultId}/review?company_id=${companyId}`,
      { comment: comment || null }
    ),
  approve: (companyId: string, periodId: string, resultId: string, approved: boolean, comment?: string) =>
    apiClient.post<GSTReconciliationResult>(
      `/gst/return-periods/${periodId}/itc/${resultId}/approve?company_id=${companyId}`,
      { approved, comment: comment || null }
    ),
};
