import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { companyService, type CompanyPayload } from "@/services/companyService";

export function useCompanies(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["companies", page, pageSize],
    queryFn: () => companyService.list(page, pageSize),
  });
}

export function useCompany(companyId: string | undefined) {
  return useQuery({
    queryKey: ["companies", companyId],
    queryFn: () => companyService.get(companyId as string),
    enabled: !!companyId,
  });
}

export function useCreateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CompanyPayload) => companyService.create(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["companies"] }),
  });
}

export function useOnboardCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CompanyPayload) => companyService.onboard(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["companies"] }),
  });
}

export function useUpdateCompany(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<CompanyPayload & { is_active: boolean }>) =>
      companyService.update(companyId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["companies"] });
      queryClient.invalidateQueries({ queryKey: ["companies", companyId] });
    },
  });
}
