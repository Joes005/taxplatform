import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type {
  ComplianceCategory,
  ComplianceControlCenterSummary,
  ComplianceFrequency,
  ComplianceHealth,
  ComplianceModule,
  ComplianceObligation,
  ComplianceObligationEvidence,
  ComplianceObligationStatus,
  CompliancePriority,
  ComplianceTask,
  ReadinessResult,
} from "@/types/compliance";

export interface ComplianceObligationCreatePayload {
  code: string;
  name: string;
  description?: string;
  category: ComplianceCategory;
  module: ComplianceModule;
  frequency: ComplianceFrequency;
  financial_year_id?: string;
  tax_period?: string;
  start_date: string;
  due_date: string;
  grace_date?: string;
  priority?: CompliancePriority;
  assigned_to?: string;
  reviewer_id?: string;
  prerequisite_config?: Record<string, unknown>;
}

export interface ObligationListFilters {
  category?: ComplianceCategory;
  module?: ComplianceModule;
  status?: ComplianceObligationStatus;
  readiness_status?: string;
  assigned_to?: string;
  search?: string;
  overdue_only?: boolean;
  page?: number;
  page_size?: number;
}

export const complianceObligationService = {
  getControlCenter: (companyId: string) =>
    apiClient.get<ComplianceControlCenterSummary>(`/compliance/control-center?company_id=${companyId}`),

  getHealth: (companyId: string) =>
    apiClient.get<ComplianceHealth>(`/compliance/health?company_id=${companyId}`),

  list: (companyId: string, filters: ObligationListFilters = {}) => {
    const params = new URLSearchParams({ company_id: companyId });
    if (filters.category) params.append("category", filters.category);
    if (filters.module) params.append("module", filters.module);
    if (filters.status) params.append("status", filters.status);
    if (filters.readiness_status) params.append("readiness_status", filters.readiness_status);
    if (filters.assigned_to) params.append("assigned_to", filters.assigned_to);
    if (filters.search) params.append("search", filters.search);
    if (filters.overdue_only) params.append("overdue_only", "true");
    if (filters.page) params.append("page", String(filters.page));
    if (filters.page_size) params.append("page_size", String(filters.page_size));

    return apiClient.get<PaginatedData<ComplianceObligation>>(`/compliance/obligations?${params.toString()}`);
  },

  get: (companyId: string, obligationId: string) =>
    apiClient.get<ComplianceObligation>(`/compliance/obligations/${obligationId}?company_id=${companyId}`),

  create: (companyId: string, payload: ComplianceObligationCreatePayload) =>
    apiClient.post<ComplianceObligation>(`/compliance/obligations?company_id=${companyId}`, payload),

  update: (companyId: string, obligationId: string, payload: Partial<ComplianceObligationCreatePayload>) =>
    apiClient.patch<ComplianceObligation>(`/compliance/obligations/${obligationId}?company_id=${companyId}`, payload),

  assign: (companyId: string, obligationId: string, assignedTo?: string | null, reviewerId?: string | null) =>
    apiClient.post<ComplianceObligation>(`/compliance/obligations/${obligationId}/assign?company_id=${companyId}`, {
      assigned_to: assignedTo || null,
      reviewer_id: reviewerId || null,
    }),

  runReadiness: (companyId: string, obligationId: string) =>
    apiClient.post<ReadinessResult>(`/compliance/obligations/${obligationId}/readiness?company_id=${companyId}`),

  submitReview: (companyId: string, obligationId: string, reviewNotes?: string) =>
    apiClient.post<ComplianceObligation>(`/compliance/obligations/${obligationId}/submit-review?company_id=${companyId}`, {
      review_notes: reviewNotes || null,
    }),

  approve: (companyId: string, obligationId: string, reviewNotes?: string) =>
    apiClient.post<ComplianceObligation>(`/compliance/obligations/${obligationId}/approve?company_id=${companyId}`, {
      review_notes: reviewNotes || null,
    }),

  reject: (companyId: string, obligationId: string, reviewNotes?: string) =>
    apiClient.post<ComplianceObligation>(`/compliance/obligations/${obligationId}/reject?company_id=${companyId}`, {
      review_notes: reviewNotes || null,
    }),

  complete: (companyId: string, obligationId: string, completionNotes?: string) =>
    apiClient.post<ComplianceObligation>(`/compliance/obligations/${obligationId}/complete?company_id=${companyId}`, {
      review_notes: completionNotes || null,
    }),

  reopen: (companyId: string, obligationId: string, reason: string) =>
    apiClient.post<ComplianceObligation>(`/compliance/obligations/${obligationId}/reopen?company_id=${companyId}`, {
      reason,
    }),

  attachEvidence: (companyId: string, obligationId: string, documentId: string, description?: string) =>
    apiClient.post<ComplianceObligationEvidence>(`/compliance/obligations/${obligationId}/evidence?company_id=${companyId}`, {
      document_id: documentId,
      description: description || null,
    }),

  listEvidence: (companyId: string, obligationId: string) =>
    apiClient.get<ComplianceObligationEvidence[]>(`/compliance/obligations/${obligationId}/evidence?company_id=${companyId}`),

  removeEvidence: (companyId: string, obligationId: string, evidenceId: string) =>
    apiClient.delete<{ deleted: boolean }>(`/compliance/obligations/${obligationId}/evidence/${evidenceId}?company_id=${companyId}`),

  generateTask: (companyId: string, obligationId: string, title?: string) =>
    apiClient.post<ComplianceTask>(`/compliance/obligations/${obligationId}/generate-task?company_id=${companyId}`, {
      title,
    }),

  sweepOverdue: (companyId: string) =>
    apiClient.post<{ marked_overdue: number }>(`/compliance/obligations/sweep-overdue?company_id=${companyId}`),

  exportObligations: (companyId: string, format: "csv" | "xlsx") =>
    apiClient.downloadBlob(`/compliance/reports/obligations/export?company_id=${companyId}&format=${format}`),

  exportReadiness: (companyId: string, format: "csv" | "xlsx") =>
    apiClient.downloadBlob(`/compliance/reports/readiness/export?company_id=${companyId}&format=${format}`),

  getExportObligationsUrl: (companyId: string, format: "csv" | "xlsx" = "csv") =>
    `/api/v1/compliance/reports/obligations/export?company_id=${companyId}&format=${format}`,

  getExportReadinessUrl: (companyId: string, format: "csv" | "xlsx" = "csv") =>
    `/api/v1/compliance/reports/readiness/export?company_id=${companyId}&format=${format}`,
};
