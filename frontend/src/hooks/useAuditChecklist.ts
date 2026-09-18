import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  auditChecklistService,
  type AuditChecklistItemCreatePayload,
  type AuditChecklistItemUpdatePayload,
} from "@/services/auditChecklistService";

const keys = {
  detail: (companyId: string, engagementId: string) => ["audit-checklist", companyId, engagementId] as const,
};

export function useAuditChecklist(companyId: string | undefined, engagementId: string | undefined) {
  return useQuery({
    queryKey: companyId && engagementId ? keys.detail(companyId, engagementId) : ["audit-checklist", "none"],
    queryFn: () => auditChecklistService.get(companyId as string, engagementId as string),
    enabled: !!companyId && !!engagementId,
  });
}

export function useAddAuditChecklistItem(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AuditChecklistItemCreatePayload) => auditChecklistService.addItem(companyId, engagementId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) }),
  });
}

export function useUpdateAuditChecklistItem(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: AuditChecklistItemUpdatePayload }) =>
      auditChecklistService.updateItem(companyId, engagementId, itemId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) }),
  });
}
