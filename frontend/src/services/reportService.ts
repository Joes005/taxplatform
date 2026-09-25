import { apiClient } from "@/lib/api-client";
import type { PartyOutstanding, SalesPurchaseSummary, TrialBalance } from "@/types/accounting";

export const reportService = {
  salesSummary: (companyId: string, dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams({ company_id: companyId });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return apiClient.get<SalesPurchaseSummary>(`/accounting/reports/sales-summary?${params.toString()}`);
  },
  purchaseSummary: (companyId: string, dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams({ company_id: companyId });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return apiClient.get<SalesPurchaseSummary>(`/accounting/reports/purchase-summary?${params.toString()}`);
  },
  customerOutstanding: (companyId: string) =>
    apiClient.get<PartyOutstanding[]>(`/accounting/reports/customer-outstanding?company_id=${companyId}`),
  vendorOutstanding: (companyId: string) =>
    apiClient.get<PartyOutstanding[]>(`/accounting/reports/vendor-outstanding?company_id=${companyId}`),
  trialBalance: (companyId: string, asOf?: string) => {
    const params = new URLSearchParams({ company_id: companyId });
    if (asOf) params.set("as_of", asOf);
    return apiClient.get<TrialBalance>(`/accounting/reports/trial-balance?${params.toString()}`);
  },
  exportSalesRegister: (companyId: string, format: "csv" | "xlsx" = "csv", dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams({ company_id: companyId, format });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return apiClient.downloadBlob(`/accounting/reports/sales-register/export?${params.toString()}`);
  },
  exportPurchaseRegister: (companyId: string, format: "csv" | "xlsx" = "csv", dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams({ company_id: companyId, format });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return apiClient.downloadBlob(`/accounting/reports/purchase-register/export?${params.toString()}`);
  },
  exportTrialBalance: (companyId: string, format: "csv" | "xlsx" = "csv", asOf?: string) => {
    const params = new URLSearchParams({ company_id: companyId, format });
    if (asOf) params.set("as_of", asOf);
    return apiClient.downloadBlob(`/accounting/reports/trial-balance/export?${params.toString()}`);
  },
};
