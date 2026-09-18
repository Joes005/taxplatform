import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deducteeService, type DeducteePayload } from "@/services/deducteeService";

const keys = {
  all: (companyId: string) => ["deductees", companyId] as const,
  list: (companyId: string, page: number, search?: string) =>
    ["deductees", companyId, "list", page, search ?? ""] as const,
  detail: (companyId: string, id: string) => ["deductees", companyId, "detail", id] as const,
};

export function useDeductees(companyId: string | undefined, page = 1, search?: string) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page, search) : ["deductees", "none"],
    queryFn: () => deducteeService.list(companyId as string, page, 20, search),
    enabled: !!companyId,
  });
}

export function useDeductee(companyId: string | undefined, deducteeId: string | undefined) {
  return useQuery({
    queryKey: companyId && deducteeId ? keys.detail(companyId, deducteeId) : ["deductees", "none"],
    queryFn: () => deducteeService.get(companyId as string, deducteeId as string),
    enabled: !!companyId && !!deducteeId,
  });
}

export function useCreateDeductee(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: DeducteePayload) => deducteeService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useUpdateDeductee(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<DeducteePayload> }) =>
      deducteeService.update(companyId, id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
