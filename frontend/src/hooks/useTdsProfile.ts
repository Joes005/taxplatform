import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { tdsProfileService, type TDSProfilePayload } from "@/services/tdsProfileService";

const keys = {
  detail: (companyId: string) => ["tds-profile", companyId] as const,
};

export function useTdsProfile(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? keys.detail(companyId) : ["tds-profile", "none"],
    queryFn: () => tdsProfileService.get(companyId as string),
    enabled: !!companyId,
    retry: false,
  });
}

export function useCreateTdsProfile(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TDSProfilePayload) => tdsProfileService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId) }),
  });
}

export function useUpdateTdsProfile(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<TDSProfilePayload>) => tdsProfileService.update(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId) }),
  });
}
