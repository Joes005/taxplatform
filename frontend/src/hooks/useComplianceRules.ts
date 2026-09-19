import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { complianceRuleService, type ComplianceRuleCreatePayload } from "@/services/complianceRuleService";
import type { ComplianceCategory, ComplianceModule } from "@/types/compliance";

export function useComplianceRules(
  companyId: string | undefined,
  params?: { category?: ComplianceCategory; module?: ComplianceModule; activeOnly?: boolean }
) {
  return useQuery({
    queryKey: companyId ? ["compliance-rules", companyId, params] : ["compliance-rules", "none"],
    queryFn: () => complianceRuleService.list(companyId as string, params),
    enabled: !!companyId,
  });
}

export function useCreateComplianceRule(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ComplianceRuleCreatePayload) => complianceRuleService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance-rules", companyId] }),
  });
}

export function useSetComplianceRuleActive(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? complianceRuleService.activate(companyId, id) : complianceRuleService.deactivate(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance-rules", companyId] }),
  });
}
