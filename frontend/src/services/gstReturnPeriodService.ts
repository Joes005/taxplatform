import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { GSTReturnPeriod } from "@/types/gst";

export interface GSTReturnPeriodPayload {
  financial_year_id: string;
  year: number;
  month: number;
}

export const gstReturnPeriodService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<GSTReturnPeriod>>(
      `/gst/return-periods?company_id=${companyId}&page=${page}&page_size=${pageSize}`
    ),
  get: (companyId: string, periodId: string) =>
    apiClient.get<GSTReturnPeriod>(`/gst/return-periods/${periodId}?company_id=${companyId}`),
  create: (companyId: string, payload: GSTReturnPeriodPayload) =>
    apiClient.post<GSTReturnPeriod>(`/gst/return-periods?company_id=${companyId}`, payload),
  exportGstr1: (companyId: string, periodId: string, format: "csv" | "xlsx" = "csv") =>
    apiClient.downloadBlob(
      `/gst/return-periods/${periodId}/reports/gstr1?company_id=${companyId}&format=${format}`
    ),
  exportGstr3b: (companyId: string, periodId: string, format: "csv" | "xlsx" = "csv") =>
    apiClient.downloadBlob(
      `/gst/return-periods/${periodId}/reports/gstr3b?company_id=${companyId}&format=${format}`
    ),
  exportReconciliation: (companyId: string, periodId: string, format: "csv" | "xlsx" = "csv") =>
    apiClient.downloadBlob(
      `/gst/return-periods/${periodId}/reports/reconciliation?company_id=${companyId}&format=${format}`
    ),
  exportItc: (companyId: string, periodId: string, format: "csv" | "xlsx" = "csv") =>
    apiClient.downloadBlob(
      `/gst/return-periods/${periodId}/reports/itc?company_id=${companyId}&format=${format}`
    ),
};
