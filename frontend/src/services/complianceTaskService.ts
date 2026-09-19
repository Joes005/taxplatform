import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type {
  ComplianceCategory,
  ComplianceModule,
  CompliancePriority,
  ComplianceSourceType,
  ComplianceTask,
  ComplianceTaskComment,
  ComplianceTaskEvidence,
  ComplianceTaskStatus,
} from "@/types/compliance";

export interface ComplianceTaskCreatePayload {
  obligation_id?: string;
  title: string;
  description?: string;
  category: ComplianceCategory;
  module: ComplianceModule;
  priority?: CompliancePriority;
  assigned_to?: string;
  reviewer_id?: string;
  start_date?: string;
  due_date: string;
  source_type?: ComplianceSourceType;
  source_id?: string;
}

export interface ComplianceTaskListFilters {
  status?: ComplianceTaskStatus;
  category?: ComplianceCategory;
  module?: ComplianceModule;
  priority?: CompliancePriority;
  assignedTo?: string;
  reviewerId?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}

function buildQuery(companyId: string, filters: ComplianceTaskListFilters = {}): string {
  const qs = new URLSearchParams({ company_id: companyId });
  if (filters.status) qs.set("status", filters.status);
  if (filters.category) qs.set("category", filters.category);
  if (filters.module) qs.set("module", filters.module);
  if (filters.priority) qs.set("priority", filters.priority);
  if (filters.assignedTo) qs.set("assigned_to", filters.assignedTo);
  if (filters.reviewerId) qs.set("reviewer_id", filters.reviewerId);
  if (filters.search) qs.set("search", filters.search);
  qs.set("page", String(filters.page ?? 1));
  qs.set("page_size", String(filters.pageSize ?? 20));
  return qs.toString();
}

export const complianceTaskService = {
  list: (companyId: string, filters: ComplianceTaskListFilters = {}) =>
    apiClient.get<PaginatedData<ComplianceTask>>(`/compliance/tasks?${buildQuery(companyId, filters)}`),
  get: (companyId: string, id: string) =>
    apiClient.get<ComplianceTask>(`/compliance/tasks/${id}?company_id=${companyId}`),
  create: (companyId: string, payload: ComplianceTaskCreatePayload) =>
    apiClient.post<ComplianceTask>(`/compliance/tasks?company_id=${companyId}`, payload),
  update: (companyId: string, id: string, payload: Partial<ComplianceTaskCreatePayload>) =>
    apiClient.patch<ComplianceTask>(`/compliance/tasks/${id}?company_id=${companyId}`, payload),
  delete: (companyId: string, id: string) => apiClient.delete<null>(`/compliance/tasks/${id}?company_id=${companyId}`),
  assign: (companyId: string, id: string, assignedTo?: string, reviewerId?: string) =>
    apiClient.post<ComplianceTask>(`/compliance/tasks/${id}/assign?company_id=${companyId}`, {
      assigned_to: assignedTo,
      reviewer_id: reviewerId,
    }),
  start: (companyId: string, id: string) => apiClient.post<ComplianceTask>(`/compliance/tasks/${id}/start?company_id=${companyId}`),
  submitReview: (companyId: string, id: string) =>
    apiClient.post<ComplianceTask>(`/compliance/tasks/${id}/submit-review?company_id=${companyId}`),
  complete: (companyId: string, id: string, completionNotes?: string) =>
    apiClient.post<ComplianceTask>(`/compliance/tasks/${id}/complete?company_id=${companyId}`, {
      completion_notes: completionNotes,
    }),
  verify: (companyId: string, id: string) => apiClient.post<ComplianceTask>(`/compliance/tasks/${id}/verify?company_id=${companyId}`),
  returnForChanges: (companyId: string, id: string, reason: string) =>
    apiClient.post<ComplianceTask>(`/compliance/tasks/${id}/return-for-changes?company_id=${companyId}`, { reason }),
  cancel: (companyId: string, id: string, reason?: string) =>
    apiClient.post<ComplianceTask>(`/compliance/tasks/${id}/cancel?company_id=${companyId}`, { reason }),
  lock: (companyId: string, id: string) => apiClient.post<ComplianceTask>(`/compliance/tasks/${id}/lock?company_id=${companyId}`),

  listComments: (companyId: string, id: string) =>
    apiClient.get<ComplianceTaskComment[]>(`/compliance/tasks/${id}/comments?company_id=${companyId}`),
  addComment: (companyId: string, id: string, comment: string) =>
    apiClient.post<ComplianceTaskComment>(`/compliance/tasks/${id}/comments?company_id=${companyId}`, { comment }),

  listEvidence: (companyId: string, id: string) =>
    apiClient.get<ComplianceTaskEvidence[]>(`/compliance/tasks/${id}/evidence?company_id=${companyId}`),
  addEvidence: (companyId: string, id: string, documentId: string, description?: string) =>
    apiClient.post<ComplianceTaskEvidence>(`/compliance/tasks/${id}/evidence?company_id=${companyId}`, {
      document_id: documentId,
      description,
    }),
  removeEvidence: (companyId: string, id: string, evidenceId: string) =>
    apiClient.delete<null>(`/compliance/tasks/${id}/evidence/${evidenceId}?company_id=${companyId}`),

  exportTasks: (companyId: string, format: "csv" | "xlsx") =>
    apiClient.downloadBlob(`/compliance/reports/tasks/export?company_id=${companyId}&format=${format}`),
};
