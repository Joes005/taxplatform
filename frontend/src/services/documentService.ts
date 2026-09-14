import { apiClient } from "@/lib/api-client";
import type { Document, DocumentStatus, DocumentType, PaginatedData } from "@/types/api";

export interface DocumentListFilters {
  companyId: string;
  page?: number;
  pageSize?: number;
  documentType?: DocumentType;
  status?: DocumentStatus;
  uploadedBy?: string;
  search?: string;
  dateFrom?: string;
  dateTo?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
}

export interface UploadDocumentPayload {
  companyId: string;
  file: File;
  documentType: DocumentType;
  description?: string;
}

export interface UpdateDocumentPayload {
  document_type?: DocumentType;
  description?: string | null;
}

function buildListQuery(filters: DocumentListFilters): string {
  const params = new URLSearchParams();
  params.set("company_id", filters.companyId);
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.pageSize ?? 20));
  if (filters.documentType) params.set("document_type", filters.documentType);
  if (filters.status) params.set("status", filters.status);
  if (filters.uploadedBy) params.set("uploaded_by", filters.uploadedBy);
  if (filters.search) params.set("search", filters.search);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.sortBy) params.set("sort_by", filters.sortBy);
  if (filters.sortDir) params.set("sort_dir", filters.sortDir);
  return params.toString();
}

export const documentService = {
  list: (filters: DocumentListFilters) =>
    apiClient.get<PaginatedData<Document>>(`/documents?${buildListQuery(filters)}`),

  get: (companyId: string, documentId: string) =>
    apiClient.get<Document>(`/documents/${documentId}?company_id=${companyId}`),

  upload: ({ companyId, file, documentType, description }: UploadDocumentPayload) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentType);
    if (description) formData.append("description", description);
    return apiClient.upload<Document>(`/documents?company_id=${companyId}`, formData);
  },

  update: (companyId: string, documentId: string, payload: UpdateDocumentPayload) =>
    apiClient.patch<Document>(`/documents/${documentId}?company_id=${companyId}`, payload),

  archive: (companyId: string, documentId: string) =>
    apiClient.patch<Document>(`/documents/${documentId}/archive?company_id=${companyId}`),

  restore: (companyId: string, documentId: string) =>
    apiClient.patch<Document>(`/documents/${documentId}/restore?company_id=${companyId}`),

  // Downloads always go through the authenticated fetch path (never a bare
  // <a href>/<iframe src> URL) because auth is a bearer token, not a
  // cookie — a plain URL has no way to attach it. Callers turn the
  // resulting Blob into an object URL for saving or previewing.
  download: (companyId: string, documentId: string) =>
    apiClient.downloadBlob(`/documents/${documentId}/download?company_id=${companyId}`),
};
