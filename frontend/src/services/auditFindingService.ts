import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type {
  AuditFinding,
  AuditFindingCategory,
  AuditFindingComment,
  AuditFindingCreateResult,
  AuditFindingEvidence,
  AuditFindingResponse,
  AuditFindingSeverity,
  AuditFindingSourceType,
  AuditFindingStatus,
} from "@/types/audit";

export interface AuditFindingCreatePayload {
  title: string;
  description?: string;
  category: AuditFindingCategory;
  severity: AuditFindingSeverity;
  source_type?: AuditFindingSourceType;
  source_id?: string;
  assigned_to?: string;
  due_date?: string;
}

export interface AuditFindingUpdatePayload {
  title?: string;
  description?: string;
  category?: AuditFindingCategory;
  severity?: AuditFindingSeverity;
  due_date?: string;
}

export const auditFindingService = {
  listForEngagement: (companyId: string, engagementId: string, page = 1, pageSize = 20, status?: AuditFindingStatus) =>
    apiClient.get<PaginatedData<AuditFinding>>(
      `/audits/engagements/${engagementId}/findings?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (status ? `&status=${status}` : "")
    ),
  listForCompany: (companyId: string, page = 1, pageSize = 20, status?: AuditFindingStatus) =>
    apiClient.get<PaginatedData<AuditFinding>>(
      `/audits/findings?company_id=${companyId}&page=${page}&page_size=${pageSize}` + (status ? `&status=${status}` : "")
    ),
  get: (companyId: string, findingId: string) =>
    apiClient.get<AuditFinding>(`/audits/findings/${findingId}?company_id=${companyId}`),
  create: (companyId: string, engagementId: string, payload: AuditFindingCreatePayload) =>
    apiClient.post<AuditFindingCreateResult>(`/audits/engagements/${engagementId}/findings?company_id=${companyId}`, payload),
  update: (companyId: string, findingId: string, payload: AuditFindingUpdatePayload) =>
    apiClient.patch<AuditFinding>(`/audits/findings/${findingId}?company_id=${companyId}`, payload),
  assign: (companyId: string, findingId: string, assignedTo: string) =>
    apiClient.post<AuditFinding>(`/audits/findings/${findingId}/assign?company_id=${companyId}`, { assigned_to: assignedTo }),
  startReview: (companyId: string, findingId: string) =>
    apiClient.post<AuditFinding>(`/audits/findings/${findingId}/start-review?company_id=${companyId}`),
  requestAction: (companyId: string, findingId: string) =>
    apiClient.post<AuditFinding>(`/audits/findings/${findingId}/request-action?company_id=${companyId}`),
  resolve: (companyId: string, findingId: string, resolutionSummary: string) =>
    apiClient.post<AuditFinding>(`/audits/findings/${findingId}/resolve?company_id=${companyId}`, {
      resolution_summary: resolutionSummary,
    }),
  close: (companyId: string, findingId: string) =>
    apiClient.post<AuditFinding>(`/audits/findings/${findingId}/close?company_id=${companyId}`),
  reopen: (companyId: string, findingId: string, reason: string) =>
    apiClient.post<AuditFinding>(`/audits/findings/${findingId}/reopen?company_id=${companyId}`, { reason }),
  reject: (companyId: string, findingId: string, reason: string) =>
    apiClient.post<AuditFinding>(`/audits/findings/${findingId}/reject?company_id=${companyId}`, { reason }),

  listComments: (companyId: string, findingId: string) =>
    apiClient.get<AuditFindingComment[]>(`/audits/findings/${findingId}/comments?company_id=${companyId}`),
  addComment: (companyId: string, findingId: string, comment: string) =>
    apiClient.post<AuditFindingComment>(`/audits/findings/${findingId}/comments?company_id=${companyId}`, { comment }),

  listEvidence: (companyId: string, findingId: string) =>
    apiClient.get<AuditFindingEvidence[]>(`/audits/findings/${findingId}/evidence?company_id=${companyId}`),
  addEvidence: (companyId: string, findingId: string, documentId: string, description?: string) =>
    apiClient.post<AuditFindingEvidence>(`/audits/findings/${findingId}/evidence?company_id=${companyId}`, {
      document_id: documentId,
      description,
    }),
  removeEvidence: (companyId: string, findingId: string, evidenceId: string) =>
    apiClient.delete<null>(`/audits/findings/${findingId}/evidence/${evidenceId}?company_id=${companyId}`),

  listResponses: (companyId: string, findingId: string) =>
    apiClient.get<AuditFindingResponse[]>(`/audits/findings/${findingId}/responses?company_id=${companyId}`),
  submitResponse: (companyId: string, findingId: string, responseText: string) =>
    apiClient.post<AuditFindingResponse>(`/audits/findings/${findingId}/responses?company_id=${companyId}`, {
      response_text: responseText,
    }),
  reviewResponse: (companyId: string, findingId: string, responseId: string, accept: boolean, reviewComment?: string) =>
    apiClient.post<AuditFindingResponse>(
      `/audits/findings/${findingId}/responses/${responseId}/review?company_id=${companyId}`,
      { accept, review_comment: reviewComment }
    ),
};
