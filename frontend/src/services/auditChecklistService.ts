import { apiClient } from "@/lib/api-client";
import type { AuditChecklist, AuditChecklistCategory, AuditChecklistItem, AuditChecklistItemStatus } from "@/types/audit";

export interface AuditChecklistItemCreatePayload {
  category: AuditChecklistCategory;
  title: string;
  description?: string;
  order_index?: number;
}

export interface AuditChecklistItemUpdatePayload {
  status?: AuditChecklistItemStatus;
  assigned_to?: string;
  notes?: string;
}

export const auditChecklistService = {
  get: (companyId: string, engagementId: string) =>
    apiClient.get<AuditChecklist>(`/audits/engagements/${engagementId}/checklist?company_id=${companyId}`),
  addItem: (companyId: string, engagementId: string, payload: AuditChecklistItemCreatePayload) =>
    apiClient.post<AuditChecklistItem>(`/audits/engagements/${engagementId}/checklist/items?company_id=${companyId}`, payload),
  updateItem: (companyId: string, engagementId: string, itemId: string, payload: AuditChecklistItemUpdatePayload) =>
    apiClient.patch<AuditChecklistItem>(
      `/audits/engagements/${engagementId}/checklist/items/${itemId}?company_id=${companyId}`,
      payload
    ),
};
