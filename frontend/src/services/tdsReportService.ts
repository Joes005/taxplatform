import { apiClient } from "@/lib/api-client";
import type {
  TDSChallanSummaryRow,
  TDSDeducteeSummaryRow,
  TDSQuarterlySummary,
  TDSSectionSummaryRow,
} from "@/types/tds";

export const tdsReportService = {
  quarterlySummary: (companyId: string, periodId: string) =>
    apiClient.get<TDSQuarterlySummary>(
      `/tds/return-periods/${periodId}/reports/summary?company_id=${companyId}`
    ),
  sectionSummary: (companyId: string, periodId: string) =>
    apiClient.get<TDSSectionSummaryRow[]>(
      `/tds/return-periods/${periodId}/reports/sections?company_id=${companyId}`
    ),
  deducteeSummary: (companyId: string, periodId: string) =>
    apiClient.get<TDSDeducteeSummaryRow[]>(
      `/tds/return-periods/${periodId}/reports/deductees?company_id=${companyId}`
    ),
  challanSummary: (companyId: string, periodId: string) =>
    apiClient.get<TDSChallanSummaryRow[]>(
      `/tds/return-periods/${periodId}/reports/challans?company_id=${companyId}`
    ),
  // Downloads go through the authenticated fetch path (never a bare
  // <a href> URL) since auth is a bearer token, not a cookie.
  exportQuarterly: (companyId: string, periodId: string, format: "csv" | "xlsx") =>
    apiClient.downloadBlob(
      `/tds/return-periods/${periodId}/reports/export/quarterly?company_id=${companyId}&format=${format}`
    ),
  exportReconciliation: (companyId: string, periodId: string, format: "csv" | "xlsx") =>
    apiClient.downloadBlob(
      `/tds/return-periods/${periodId}/reports/export/reconciliation?company_id=${companyId}&format=${format}`
    ),
};
