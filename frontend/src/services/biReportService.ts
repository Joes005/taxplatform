import { apiClient } from "@/lib/api-client";
import type {
  TrialBalanceReport,
  ProfitLossReport,
  BalanceSheetReport,
  GeneralLedgerReport,
  ReceivablesPayablesReport,
  AgeingReport,
  AnalyticsReport,
  CashBankReport,
  GSTPeriodSummary,
  TDSReportSummary,
  IncomeTaxReportSummary,
  AuditReportSummary,
  ComplianceReportSummary,
  ManagementDashboardReport,
} from "@/types/reports";

export interface ReportFilterParams {
  financial_year_id?: string;
  as_of?: string;
  date_from?: string;
  date_to?: string;
  compare_previous?: boolean;
}

export const biReportService = {
  getManagementDashboard: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    return apiClient.get<ManagementDashboardReport>(`/reports/management?${sp.toString()}`);
  },

  getTrialBalance: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId });
    if (params.as_of) sp.set("as_of", params.as_of);
    if (params.financial_year_id) sp.set("financial_year_id", params.financial_year_id);
    return apiClient.get<TrialBalanceReport>(`/reports/trial-balance?${sp.toString()}`);
  },

  getProfitLoss: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    if (params.compare_previous) sp.set("compare_previous", "true");
    return apiClient.get<ProfitLossReport>(`/reports/profit-loss?${sp.toString()}`);
  },

  getBalanceSheet: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId });
    if (params.as_of) sp.set("as_of", params.as_of);
    return apiClient.get<BalanceSheetReport>(`/reports/balance-sheet?${sp.toString()}`);
  },

  getGeneralLedger: (
    companyId: string,
    ledgerId: string,
    params: { date_from?: string; date_to?: string } = {}
  ) => {
    const sp = new URLSearchParams({ company_id: companyId, ledger_id: ledgerId });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    return apiClient.get<GeneralLedgerReport>(`/reports/general-ledger?${sp.toString()}`);
  },

  getReceivables: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    return apiClient.get<ReceivablesPayablesReport>(`/reports/receivables?${sp.toString()}`);
  },

  getPayables: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    return apiClient.get<ReceivablesPayablesReport>(`/reports/payables?${sp.toString()}`);
  },

  getAgeing: (companyId: string, kind: "RECEIVABLES" | "PAYABLES", asOf?: string) => {
    const sp = new URLSearchParams({ company_id: companyId, kind });
    if (asOf) sp.set("as_of", asOf);
    return apiClient.get<AgeingReport>(`/reports/ageing?${sp.toString()}`);
  },

  getSalesAnalytics: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId, kind: "SALES" });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    return apiClient.get<AnalyticsReport>(`/reports/sales?${sp.toString()}`);
  },

  getPurchaseAnalytics: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId, kind: "PURCHASE" });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    return apiClient.get<AnalyticsReport>(`/reports/sales?${sp.toString()}`);
  },

  getCashBank: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    return apiClient.get<CashBankReport>(`/reports/cash-bank?${sp.toString()}`);
  },

  getGstSummary: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    return apiClient.get<GSTPeriodSummary>(`/reports/gst?${sp.toString()}`);
  },

  getTdsSummary: (companyId: string, params: ReportFilterParams = {}) => {
    const sp = new URLSearchParams({ company_id: companyId });
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);
    return apiClient.get<TDSReportSummary>(`/reports/tds?${sp.toString()}`);
  },

  getAuditSummary: (companyId: string) => {
    const sp = new URLSearchParams({ company_id: companyId });
    return apiClient.get<AuditReportSummary>(`/reports/audit?${sp.toString()}`);
  },

  getComplianceSummary: (companyId: string) => {
    const sp = new URLSearchParams({ company_id: companyId });
    return apiClient.get<ComplianceReportSummary>(`/reports/compliance?${sp.toString()}`);
  },

  getIncomeTaxSummary: (companyId: string) => {
    const sp = new URLSearchParams({ company_id: companyId });
    return apiClient.get<IncomeTaxReportSummary>(`/reports/income-tax?${sp.toString()}`);
  },

  exportReport: async (
    companyId: string,
    reportType: string,
    format: "CSV" | "XLSX",
    params: ReportFilterParams = {}
  ) => {
    const sp = new URLSearchParams({
      company_id: companyId,
      report_type: reportType,
      format,
    });
    if (params.as_of) sp.set("as_of", params.as_of);
    if (params.date_from) sp.set("date_from", params.date_from);
    if (params.date_to) sp.set("date_to", params.date_to);

    const { blob, filename } = await apiClient.downloadBlob(`/reports/export?${sp.toString()}`);
    const downloadName = filename ?? `${reportType.toLowerCase()}_report.${format.toLowerCase()}`;
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", downloadName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
