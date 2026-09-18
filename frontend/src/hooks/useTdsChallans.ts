import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { tdsChallanService, type TDSChallanPayload } from "@/services/tdsChallanService";
import type { TDSChallanStatus } from "@/types/tds";

const keys = {
  all: (companyId: string) => ["tds-challans", companyId] as const,
  list: (companyId: string, page: number) => ["tds-challans", companyId, "list", page] as const,
  detail: (companyId: string, id: string) => ["tds-challans", companyId, "detail", id] as const,
};

export function useTdsChallans(companyId: string | undefined, page = 1, financialYearId?: string) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page) : ["tds-challans", "none"],
    queryFn: () => tdsChallanService.list(companyId as string, page, 20, financialYearId),
    enabled: !!companyId,
  });
}

export function useTdsChallan(companyId: string | undefined, challanId: string | undefined) {
  return useQuery({
    queryKey: companyId && challanId ? keys.detail(companyId, challanId) : ["tds-challans", "none"],
    queryFn: () => tdsChallanService.get(companyId as string, challanId as string),
    enabled: !!companyId && !!challanId,
  });
}

export function useCreateTdsChallan(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TDSChallanPayload) => tdsChallanService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useUpdateTdsChallanStatus(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: TDSChallanStatus }) =>
      tdsChallanService.updateStatus(companyId, id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useAllocateTdsChallan(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ challanId, transactionId, amount }: { challanId: string; transactionId: string; amount: string }) =>
      tdsChallanService.allocate(companyId, challanId, transactionId, amount),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.all(companyId) });
      qc.invalidateQueries({ queryKey: ["tds-transactions", companyId] });
    },
  });
}
