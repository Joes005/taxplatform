import { useQuery } from "@tanstack/react-query";

import { reportService } from "@/services/reportService";

export function useSalesSummary(companyId: string | undefined, dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["reports", "sales-summary", companyId, dateFrom, dateTo],
    queryFn: () => reportService.salesSummary(companyId as string, dateFrom, dateTo),
    enabled: !!companyId,
  });
}

export function usePurchaseSummary(companyId: string | undefined, dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["reports", "purchase-summary", companyId, dateFrom, dateTo],
    queryFn: () => reportService.purchaseSummary(companyId as string, dateFrom, dateTo),
    enabled: !!companyId,
  });
}

export function useCustomerOutstanding(companyId: string | undefined) {
  return useQuery({
    queryKey: ["reports", "customer-outstanding", companyId],
    queryFn: () => reportService.customerOutstanding(companyId as string),
    enabled: !!companyId,
  });
}

export function useVendorOutstanding(companyId: string | undefined) {
  return useQuery({
    queryKey: ["reports", "vendor-outstanding", companyId],
    queryFn: () => reportService.vendorOutstanding(companyId as string),
    enabled: !!companyId,
  });
}

export function useTrialBalance(companyId: string | undefined, asOf?: string) {
  return useQuery({
    queryKey: ["reports", "trial-balance", companyId, asOf],
    queryFn: () => reportService.trialBalance(companyId as string, asOf),
    enabled: !!companyId,
  });
}
