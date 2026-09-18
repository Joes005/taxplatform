import { useQuery } from "@tanstack/react-query";

import { auditReportService } from "@/services/auditReportService";

export function useAuditDashboard(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? ["audit-dashboard", companyId] : ["audit-dashboard", "none"],
    queryFn: () => auditReportService.dashboard(companyId as string),
    enabled: !!companyId,
  });
}

export function useAuditEngagementProgress(companyId: string | undefined, engagementId: string | undefined) {
  return useQuery({
    queryKey: companyId && engagementId ? ["audit-engagement-progress", companyId, engagementId] : ["audit-engagement-progress", "none"],
    queryFn: () => auditReportService.engagementProgress(companyId as string, engagementId as string),
    enabled: !!companyId && !!engagementId,
  });
}
