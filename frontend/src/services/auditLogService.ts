import { apiClient } from "@/lib/api-client";
import type { AuditLog, PaginatedData } from "@/types/api";

export interface AuditLogFilters {
  companyId: string;
  action?: string;
  userId?: string;
  resourceType?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
}

export const auditLogService = {
  list: (filters: AuditLogFilters) => {
    const params = new URLSearchParams();
    params.set("company_id", filters.companyId);
    if (filters.action) params.set("action", filters.action);
    if (filters.userId) params.set("user_id", filters.userId);
    if (filters.resourceType) params.set("resource_type", filters.resourceType);
    if (filters.dateFrom) params.set("date_from", filters.dateFrom);
    if (filters.dateTo) params.set("date_to", filters.dateTo);
    params.set("page", String(filters.page ?? 1));
    params.set("page_size", String(filters.pageSize ?? 20));

    return apiClient.get<PaginatedData<AuditLog>>(`/audit-logs?${params.toString()}`);
  },
};
