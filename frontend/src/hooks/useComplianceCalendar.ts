import { useQuery } from "@tanstack/react-query";

import { complianceCalendarService } from "@/services/complianceCalendarService";

export function useComplianceCalendarMonth(companyId: string | undefined, year: number, month: number) {
  return useQuery({
    queryKey: companyId ? ["compliance-calendar", companyId, year, month] : ["compliance-calendar", "none"],
    queryFn: () => complianceCalendarService.month(companyId as string, year, month),
    enabled: !!companyId,
  });
}

export function useComplianceDashboard(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? ["compliance-dashboard", companyId] : ["compliance-dashboard", "none"],
    queryFn: () => complianceCalendarService.dashboard(companyId as string),
    enabled: !!companyId,
  });
}
