import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { tdsReconciliationService } from "@/services/tdsReconciliationService";

const keys = {
  list: (companyId: string, financialYearId?: string) =>
    ["tds-reconciliation", companyId, financialYearId ?? "all"] as const,
};

export function useTdsReconciliation(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, financialYearId) : ["tds-reconciliation", "none"],
    queryFn: () => tdsReconciliationService.list(companyId as string, financialYearId),
    enabled: !!companyId,
  });
}

export function useRunTdsReconciliation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (financialYearId: string) => tdsReconciliationService.run(companyId, financialYearId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tds-reconciliation", companyId] }),
  });
}
