import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { itrPreparationService } from "@/services/itrPreparationService";

const keys = {
  all: (companyId: string) => ["itr-preparations", companyId] as const,
  list: (companyId: string, page: number) => ["itr-preparations", companyId, "list", page] as const,
  detail: (companyId: string, id: string) => ["itr-preparations", companyId, "detail", id] as const,
};

export function useItrPreparations(companyId: string | undefined, page = 1) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page) : ["itr-preparations", "none"],
    queryFn: () => itrPreparationService.list(companyId as string, page),
    enabled: !!companyId,
  });
}

export function useItrPreparation(companyId: string | undefined, id: string | undefined) {
  return useQuery({
    queryKey: companyId && id ? keys.detail(companyId, id) : ["itr-preparations", "none"],
    queryFn: () => itrPreparationService.get(companyId as string, id as string),
    enabled: !!companyId && !!id,
  });
}

export function useCreateItrPreparation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taxComputationId: string) => itrPreparationService.create(companyId, taxComputationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

function useItrAction(companyId: string, id: string, fn: (companyId: string, id: string) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => fn(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, id) }),
  });
}

export function useValidateItrPreparation(companyId: string, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => itrPreparationService.validate(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, id) }),
  });
}
export function useSubmitItrPreparationForReview(companyId: string, id: string) {
  return useItrAction(companyId, id, itrPreparationService.submitForReview);
}
export function useApproveItrPreparation(companyId: string, id: string) {
  return useItrAction(companyId, id, itrPreparationService.approve);
}
export function useLockItrPreparation(companyId: string, id: string) {
  return useItrAction(companyId, id, itrPreparationService.lock);
}
