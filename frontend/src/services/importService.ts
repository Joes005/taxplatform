import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type {
  FieldDefinition,
  ImportErrorRow,
  ImportJob,
  ImportRow,
  ImportType,
} from "@/types/accounting";

export interface ImportColumnPreview {
  columns: string[];
  sample_rows: Record<string, string>[];
}

export interface CreateImportJobPayload {
  document_id: string;
  import_type: ImportType;
  financial_year_id?: string | null;
  return_period_id?: string | null;
  column_mapping: Record<string, string>;
}

export const importService = {
  getFields: (importType: ImportType) =>
    apiClient.get<FieldDefinition[]>(`/accounting/imports/fields?import_type=${importType}`),

  previewColumns: (companyId: string, documentId: string, importType: ImportType) =>
    apiClient.get<ImportColumnPreview>(
      `/accounting/imports/preview-columns?company_id=${companyId}&document_id=${documentId}&import_type=${importType}`
    ),

  create: (companyId: string, payload: CreateImportJobPayload) =>
    apiClient.post<ImportJob>(`/accounting/imports?company_id=${companyId}`, payload),

  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<ImportJob>>(
      `/accounting/imports?company_id=${companyId}&page=${page}&page_size=${pageSize}`
    ),

  get: (companyId: string, jobId: string) =>
    apiClient.get<ImportJob>(`/accounting/imports/${jobId}?company_id=${companyId}`),

  preview: (companyId: string, jobId: string, status?: string, page = 1, pageSize = 50) => {
    const params = new URLSearchParams({
      company_id: companyId,
      page: String(page),
      page_size: String(pageSize),
    });
    if (status) params.set("status", status);
    return apiClient.get<PaginatedData<ImportRow>>(
      `/accounting/imports/${jobId}/preview?${params.toString()}`
    );
  },

  errors: (companyId: string, jobId: string, page = 1, pageSize = 50) =>
    apiClient.get<PaginatedData<ImportErrorRow>>(
      `/accounting/imports/${jobId}/errors?company_id=${companyId}&page=${page}&page_size=${pageSize}`
    ),

  commit: (companyId: string, jobId: string) =>
    apiClient.post<ImportJob>(`/accounting/imports/${jobId}/commit?company_id=${companyId}`),

  cancel: (companyId: string, jobId: string) =>
    apiClient.post<ImportJob>(`/accounting/imports/${jobId}/cancel?company_id=${companyId}`),
};
