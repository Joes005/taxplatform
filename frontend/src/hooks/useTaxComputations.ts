import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { taxComputationService } from "@/services/taxComputationService";
import type { TaxRegime } from "@/types/incomeTax";

const keys = {
  all: (companyId: string) => ["tax-computations", companyId] as const,
  list: (companyId: string, page: number) => ["tax-computations", companyId, "list", page] as const,
  detail: (companyId: string, id: string) => ["tax-computations", companyId, "detail", id] as const,
  snapshots: (companyId: string, id: string) => ["tax-computations", companyId, "snapshots", id] as const,
};

export function useTaxComputations(companyId: string | undefined, page = 1) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page) : ["tax-computations", "none"],
    queryFn: () => taxComputationService.list(companyId as string, page),
    enabled: !!companyId,
  });
}

export function useTaxComputation(companyId: string | undefined, id: string | undefined) {
  return useQuery({
    queryKey: companyId && id ? keys.detail(companyId, id) : ["tax-computations", "none"],
    queryFn: () => taxComputationService.get(companyId as string, id as string),
    enabled: !!companyId && !!id,
  });
}

export function useTaxComputationSnapshots(companyId: string | undefined, id: string | undefined) {
  return useQuery({
    queryKey: companyId && id ? keys.snapshots(companyId, id) : ["tax-computations", "none"],
    queryFn: () => taxComputationService.listSnapshots(companyId as string, id as string),
    enabled: !!companyId && !!id,
  });
}

export function useCreateTaxComputation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ financialYearId, taxRegime }: { financialYearId: string; taxRegime: TaxRegime }) =>
      taxComputationService.create(companyId, financialYearId, taxRegime),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

function useComputationAction(companyId: string, id: string, fn: (companyId: string, id: string) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => fn(companyId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, id) });
      qc.invalidateQueries({ queryKey: keys.snapshots(companyId, id) });
      qc.invalidateQueries({ queryKey: keys.all(companyId) });
    },
  });
}

export function useCalculateTaxComputation(companyId: string, id: string) {
  return useComputationAction(companyId, id, taxComputationService.calculate);
}
export function useSubmitTaxComputationForReview(companyId: string, id: string) {
  return useComputationAction(companyId, id, taxComputationService.submitForReview);
}
export function useApproveTaxComputation(companyId: string, id: string) {
  return useComputationAction(companyId, id, taxComputationService.approve);
}
export function useLockTaxComputation(companyId: string, id: string) {
  return useComputationAction(companyId, id, taxComputationService.lock);
}
export function useCancelTaxComputation(companyId: string, id: string) {
  return useComputationAction(companyId, id, taxComputationService.cancel);
}
