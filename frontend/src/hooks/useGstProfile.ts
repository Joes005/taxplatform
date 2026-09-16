import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { gstProfileService, type GSTProfilePayload } from "@/services/gstProfileService";

const keys = {
  detail: (companyId: string) => ["gst-profile", companyId] as const,
};

export function useGstProfile(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? keys.detail(companyId) : ["gst-profile", "none"],
    queryFn: () => gstProfileService.get(companyId as string),
    enabled: !!companyId,
    retry: false,
  });
}

export function useCreateGstProfile(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: GSTProfilePayload) => gstProfileService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId) }),
  });
}

export function useUpdateGstProfile(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<GSTProfilePayload>) => gstProfileService.update(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId) }),
  });
}
