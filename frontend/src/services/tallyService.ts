import { apiClient } from "@/lib/api-client";

export type TallyFormat = "TALLY_XML" | "XML" | "CSV" | "XLSX" | "UNKNOWN";

export interface FileInspectionResult {
  detected_format: TallyFormat;
  encoding: string;
  size_bytes: number;
  is_valid: boolean;
  is_empty: boolean;
  error?: string | null;
  sample_headers?: string[];
  sample_rows?: Record<string, unknown>[];
  company_name?: string | null;
}

export interface TallyMappingRule {
  source_type: "LEDGER" | "PARTY" | "TAX" | "GROUP" | "STOCK_ITEM";
  source_name: string;
  source_group?: string | null;
  target_id?: string | null;
  target_name?: string | null;
  status: "EXACT" | "CONFIRMED" | "MANUAL" | "PROPOSED" | "UNMAPPED" | "CREATED_NEW";
  confidence: number;
  notes?: string | null;
}

export interface TallyReconciliationItem {
  entity_type: string;
  source_count: number;
  imported_count: number;
  difference_count: number;
  source_amount: string | number;
  imported_amount: string | number;
  difference_amount: string | number;
  status: string;
}

export interface TallyReconciliationReport {
  overall_matched: boolean;
  items: TallyReconciliationItem[];
  unmatched_reasons: string[];
}

export interface TallyPreviewRow {
  row_number: number;
  voucher_type: string;
  voucher_number: string;
  voucher_date: string;
  party_name?: string | null;
  amount: string | number;
  is_duplicate: boolean;
  status: string;
}

export interface TallyPreviewData {
  job_id: string;
  detected_format: string;
  company_info?: Record<string, unknown> | null;
  total_records: number;
  valid_records: number;
  duplicate_records: number;
  error_records: number;
  warning_records: number;
  mappings: TallyMappingRule[];
  reconciliation_preview: Record<string, unknown>;
  errors: Array<{
    code: string;
    message: string;
    entity: string;
    row_ref: string | number;
    severity: string;
  }>;
  rows: TallyPreviewRow[];
}

export interface TallyCommitRequest {
  job_id: string;
  confirmed_mappings?: TallyMappingRule[];
  save_as_template_name?: string | null;
}

export interface TallyCommitResponse {
  job_id: string;
  status: string;
  successful_rows: number;
  failed_rows: number;
  duplicate_rows: number;
  reconciliation: TallyReconciliationReport;
}

export interface TallyMappingTemplate {
  id: string;
  company_id: string;
  name: string;
  description?: string | null;
  source_version?: string | null;
  rules: TallyMappingRule[];
  created_at: string;
}

export interface TallyExportPreview {
  total_vouchers: number;
  voucher_breakdown: Record<string, number>;
  total_amount: string | number;
  ledgers_count: number;
  parties_count: number;
  earliest_date?: string | null;
  latest_date?: string | null;
}

export interface TallyExportRequest {
  format: "XML" | "CSV" | "XLSX";
  financial_year_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  voucher_types?: string[];
}

export const tallyService = {
  detectFile: (companyId: string, documentId: string) =>
    apiClient.post<FileInspectionResult>(`/tally/detect?company_id=${companyId}`, {
      document_id: documentId,
    }),

  preview: (companyId: string, payload: { document_id: string; template_id?: string | null; financial_year_id?: string | null }) =>
    apiClient.post<TallyPreviewData>(`/tally/preview?company_id=${companyId}`, payload),

  commit: (companyId: string, payload: TallyCommitRequest) =>
    apiClient.post<TallyCommitResponse>(`/tally/commit?company_id=${companyId}`, payload),

  getReconciliation: (companyId: string, jobId: string) =>
    apiClient.get<TallyReconciliationReport>(`/tally/reconciliation/${jobId}?company_id=${companyId}`),

  listTemplates: (companyId: string) =>
    apiClient.get<TallyMappingTemplate[]>(`/tally/templates?company_id=${companyId}`),

  createTemplate: (companyId: string, payload: { name: string; description?: string; source_version?: string; rules: TallyMappingRule[] }) =>
    apiClient.post<TallyMappingTemplate>(`/tally/templates?company_id=${companyId}`, payload),

  deleteTemplate: (companyId: string, templateId: string) =>
    apiClient.delete(`/tally/templates/${templateId}?company_id=${companyId}`),

  previewExport: (companyId: string, payload: { financial_year_id?: string; start_date?: string; end_date?: string; voucher_types?: string[] }) =>
    apiClient.post<TallyExportPreview>(`/tally/export/preview?company_id=${companyId}`, payload),

  exportData: async (companyId: string, payload: TallyExportRequest): Promise<Blob> => {
    const url = `/api/v1/tally/export?company_id=${companyId}`;
    const token = localStorage.getItem("token") || "";
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    return response.blob();
  },
};
