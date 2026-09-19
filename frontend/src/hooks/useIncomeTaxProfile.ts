import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  incomeTaxProfileService,
  type IncomeTaxProfileCreatePayload,
} from "@/services/incomeTaxProfileService";

export function useIncomeTaxProfile(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? ["income-tax-profile", companyId] : ["income-tax-profile", "none"],
    queryFn: () => incomeTaxProfileService.get(companyId as string),
    enabled: !!companyId,
    retry: false,
  });
}

export function useCreateIncomeTaxProfile(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: IncomeTaxProfileCreatePayload) => incomeTaxProfileService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-profile", companyId] }),
  });
}

export function useUpdateIncomeTaxProfile(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<IncomeTaxProfileCreatePayload>) =>
      incomeTaxProfileService.update(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-profile", companyId] }),
  });
}

export function useIncomeTaxRuleSets(companyId: string | undefined, assessmentYear: string | undefined) {
  return useQuery({
    queryKey: companyId && assessmentYear ? ["income-tax-rule-sets", companyId, assessmentYear] : ["income-tax-rule-sets", "none"],
    queryFn: () => incomeTaxProfileService.listRuleSets(companyId as string, assessmentYear as string),
    enabled: !!companyId && !!assessmentYear,
  });
}
