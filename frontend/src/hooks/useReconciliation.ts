import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { reconciliationService } from "@/services/reconciliationService";

const keys = {
  latest: (companyId: string, periodId: string) => ["reconciliation", companyId, periodId] as const,
  results: (companyId: string, periodId: string, status?: string) =>
    ["reconciliation", companyId, periodId, "results", status] as const,
};

export function useLatestReconciliation(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: companyId && periodId ? keys.latest(companyId, periodId) : ["reconciliation", "none"],
    queryFn: () => reconciliationService.getLatest(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
    retry: false,
  });
}

export function useReconciliationResults(
  companyId: string | undefined,
  periodId: string | undefined,
  status?: string
) {
  return useQuery({
    queryKey: companyId && periodId ? keys.results(companyId, periodId, status) : ["reconciliation", "none"],
    queryFn: () => reconciliationService.listResults(companyId as string, periodId as string, { status }),
    enabled: !!companyId && !!periodId,
  });
}

export function useRunReconciliation(companyId: string, periodId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => reconciliationService.run(companyId, periodId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reconciliation", companyId, periodId] }),
  });
}
