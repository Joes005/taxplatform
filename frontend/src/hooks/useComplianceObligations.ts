import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  complianceObligationService,
  type ComplianceObligationCreatePayload,
} from "@/services/complianceObligationService";

export function useComplianceObligations(companyId: string | undefined, page = 1) {
  return useQuery({
    queryKey: companyId ? ["compliance-obligations", companyId, page] : ["compliance-obligations", "none"],
    queryFn: () => complianceObligationService.list(companyId as string, page),
    enabled: !!companyId,
  });
}

export function useCreateComplianceObligation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ComplianceObligationCreatePayload) => complianceObligationService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] }),
  });
}

export function useGenerateComplianceTask(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obligationId, title }: { obligationId: string; title?: string }) =>
      complianceObligationService.generateTask(companyId, obligationId, title),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance-tasks", companyId] }),
  });
}
