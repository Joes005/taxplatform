import { useQuery } from "@tanstack/react-query";

import { auditLogService, type AuditLogFilters } from "@/services/auditLogService";

export function useAuditLogs(filters: AuditLogFilters | null) {
  return useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () => auditLogService.list(filters as AuditLogFilters),
    enabled: !!filters?.companyId,
  });
}
