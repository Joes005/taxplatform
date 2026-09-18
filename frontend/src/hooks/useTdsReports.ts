import { useQuery } from "@tanstack/react-query";

import { tdsReportService } from "@/services/tdsReportService";

export function useTdsQuarterlySummary(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: ["tds-report-summary", companyId, periodId],
    queryFn: () => tdsReportService.quarterlySummary(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}

export function useTdsSectionSummary(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: ["tds-report-sections", companyId, periodId],
    queryFn: () => tdsReportService.sectionSummary(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}

export function useTdsDeducteeSummary(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: ["tds-report-deductees", companyId, periodId],
    queryFn: () => tdsReportService.deducteeSummary(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}

export function useTdsChallanReportSummary(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: ["tds-report-challans", companyId, periodId],
    queryFn: () => tdsReportService.challanSummary(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}
