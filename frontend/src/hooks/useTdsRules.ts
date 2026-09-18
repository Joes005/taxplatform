import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { tdsRuleService, tdsSectionService, type TDSRulePayload } from "@/services/tdsRuleService";

const keys = {
  sections: (companyId: string) => ["tds-sections", companyId] as const,
  rules: (companyId: string, sectionId?: string) => ["tds-rules", companyId, sectionId ?? "all"] as const,
};

export function useTdsSections(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? keys.sections(companyId) : ["tds-sections", "none"],
    queryFn: () => tdsSectionService.list(companyId as string),
    enabled: !!companyId,
  });
}

export function useTdsRules(companyId: string | undefined, sectionId?: string) {
  return useQuery({
    queryKey: companyId ? keys.rules(companyId, sectionId) : ["tds-rules", "none"],
    queryFn: () => tdsRuleService.list(companyId as string, sectionId),
    enabled: !!companyId,
  });
}

export function useCreateTdsRule(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TDSRulePayload) => tdsRuleService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tds-rules", companyId] }),
  });
}
