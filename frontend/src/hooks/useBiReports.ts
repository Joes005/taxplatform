import { useQuery, useMutation } from "@tanstack/react-query";
import { biReportService, type ReportFilterParams } from "@/services/biReportService";

export function useManagementDashboard(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "management", companyId, params],
    queryFn: () => biReportService.getManagementDashboard(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useTrialBalance(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "trial-balance", companyId, params],
    queryFn: () => biReportService.getTrialBalance(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useProfitLoss(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "profit-loss", companyId, params],
    queryFn: () => biReportService.getProfitLoss(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useBalanceSheet(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "balance-sheet", companyId, params],
    queryFn: () => biReportService.getBalanceSheet(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useGeneralLedger(
  companyId?: string,
  ledgerId?: string,
  params?: { date_from?: string; date_to?: string }
) {
  return useQuery({
    queryKey: ["reports", "general-ledger", companyId, ledgerId, params],
    queryFn: () => biReportService.getGeneralLedger(companyId!, ledgerId!, params),
    enabled: Boolean(companyId && ledgerId),
    staleTime: 60 * 1000,
  });
}

export function useReceivables(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "receivables", companyId, params],
    queryFn: () => biReportService.getReceivables(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function usePayables(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "payables", companyId, params],
    queryFn: () => biReportService.getPayables(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useAgeing(companyId?: string, kind: "RECEIVABLES" | "PAYABLES" = "RECEIVABLES", asOf?: string) {
  return useQuery({
    queryKey: ["reports", "ageing", companyId, kind, asOf],
    queryFn: () => biReportService.getAgeing(companyId!, kind, asOf),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useSalesAnalytics(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "analytics", "sales", companyId, params],
    queryFn: () => biReportService.getSalesAnalytics(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function usePurchaseAnalytics(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "analytics", "purchase", companyId, params],
    queryFn: () => biReportService.getPurchaseAnalytics(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useCashBank(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "cash-bank", companyId, params],
    queryFn: () => biReportService.getCashBank(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useGstSummary(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "gst", companyId, params],
    queryFn: () => biReportService.getGstSummary(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useTdsSummary(companyId?: string, params?: ReportFilterParams) {
  return useQuery({
    queryKey: ["reports", "tds", companyId, params],
    queryFn: () => biReportService.getTdsSummary(companyId!, params),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useAuditSummary(companyId?: string) {
  return useQuery({
    queryKey: ["reports", "audit", companyId],
    queryFn: () => biReportService.getAuditSummary(companyId!),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useComplianceSummary(companyId?: string) {
  return useQuery({
    queryKey: ["reports", "compliance", companyId],
    queryFn: () => biReportService.getComplianceSummary(companyId!),
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
  });
}

export function useExportReport() {
  return useMutation({
    mutationFn: ({
      companyId,
      reportType,
      format,
      params,
    }: {
      companyId: string;
      reportType: string;
      format: "CSV" | "XLSX";
      params?: ReportFilterParams;
    }) => biReportService.exportReport(companyId, reportType, format, params),
  });
}
