import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { AuditAssignment, AuditAssignmentRole, AuditEngagement, AuditEngagementType, AuditSignOff, AuditSignOffType } from "@/types/audit";

export interface AuditEngagementCreatePayload {
  title: string;
  description?: string;
  financial_year_id: string;
  period_start: string;
  period_end: string;
  engagement_type: AuditEngagementType;
}

export interface AuditEngagementUpdatePayload {
  title?: string;
  description?: string;
  engagement_type?: AuditEngagementType;
}

export const auditEngagementService = {
  list: (companyId: string, page = 1, pageSize = 20, status?: string) =>
    apiClient.get<PaginatedData<AuditEngagement>>(
      `/audits/engagements?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (status ? `&status=${status}` : "")
    ),
  get: (companyId: string, engagementId: string) =>
    apiClient.get<AuditEngagement>(`/audits/engagements/${engagementId}?company_id=${companyId}`),
  create: (companyId: string, payload: AuditEngagementCreatePayload) =>
    apiClient.post<AuditEngagement>(`/audits/engagements?company_id=${companyId}`, payload),
  update: (companyId: string, engagementId: string, payload: AuditEngagementUpdatePayload) =>
    apiClient.patch<AuditEngagement>(`/audits/engagements/${engagementId}?company_id=${companyId}`, payload),

  open: (companyId: string, engagementId: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/open?company_id=${companyId}`),
  startReview: (companyId: string, engagementId: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/start-review?company_id=${companyId}`),
  requestClientAction: (companyId: string, engagementId: string, comment?: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/request-client-action?company_id=${companyId}`, { comment }),
  resumeReview: (companyId: string, engagementId: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/resume-review?company_id=${companyId}`),
  submitForReview: (companyId: string, engagementId: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/submit-for-review?company_id=${companyId}`),
  approve: (companyId: string, engagementId: string, comment?: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/approve?company_id=${companyId}`, { comment }),
  returnForChanges: (companyId: string, engagementId: string, comment?: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/return-for-changes?company_id=${companyId}`, { comment }),
  markSignedOff: (companyId: string, engagementId: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/mark-signed-off?company_id=${companyId}`),
  close: (companyId: string, engagementId: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/close?company_id=${companyId}`),
  cancel: (companyId: string, engagementId: string, comment?: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/cancel?company_id=${companyId}`, { comment }),
  lock: (companyId: string, engagementId: string) =>
    apiClient.post<AuditEngagement>(`/audits/engagements/${engagementId}/lock?company_id=${companyId}`),

  createSignOff: (companyId: string, engagementId: string, signOffType: AuditSignOffType) =>
    apiClient.post<AuditSignOff>(`/audits/engagements/${engagementId}/sign-offs?company_id=${companyId}`, { sign_off_type: signOffType }),
  listSignOffs: (companyId: string, engagementId: string) =>
    apiClient.get<AuditSignOff[]>(`/audits/engagements/${engagementId}/sign-offs?company_id=${companyId}`),

  listAssignments: (companyId: string, engagementId: string) =>
    apiClient.get<AuditAssignment[]>(`/audits/engagements/${engagementId}/assignments?company_id=${companyId}`),
  assign: (companyId: string, engagementId: string, userId: string, role: AuditAssignmentRole) =>
    apiClient.post<AuditAssignment>(`/audits/engagements/${engagementId}/assignments?company_id=${companyId}`, {
      user_id: userId,
      role,
    }),
  unassign: (companyId: string, engagementId: string, assignmentId: string) =>
    apiClient.delete<AuditAssignment>(
      `/audits/engagements/${engagementId}/assignments/${assignmentId}?company_id=${companyId}`
    ),
};
