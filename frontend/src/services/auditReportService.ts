import { apiClient } from "@/lib/api-client";
import type { AuditEngagementProgress, AuditWorkflowDashboard } from "@/types/audit";

export const auditReportService = {
  dashboard: (companyId: string) =>
    apiClient.get<AuditWorkflowDashboard>(`/audits/dashboard?company_id=${companyId}`),
  engagementProgress: (companyId: string, engagementId: string) =>
    apiClient.get<AuditEngagementProgress>(`/audits/engagements/${engagementId}/progress?company_id=${companyId}`),
  exportFindings: (companyId: string, engagementId: string, format: "csv" | "xlsx") =>
    apiClient.downloadBlob(`/audits/engagements/${engagementId}/export?company_id=${companyId}&format=${format}`),
};
