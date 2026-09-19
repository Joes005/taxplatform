import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { incomeTaxCapitalGainService, type CapitalGainPayload } from "@/services/incomeTaxCapitalGainService";

export function useCapitalGains(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["income-tax-capital-gains", companyId, financialYearId] : ["income-tax-capital-gains", "none"],
    queryFn: () => incomeTaxCapitalGainService.list(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}

export function useCreateCapitalGain(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CapitalGainPayload) => incomeTaxCapitalGainService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-capital-gains", companyId] }),
  });
}

export function useDeleteCapitalGain(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => incomeTaxCapitalGainService.delete(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-capital-gains", companyId] }),
  });
}
