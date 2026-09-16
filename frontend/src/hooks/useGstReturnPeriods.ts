import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { gstReturnPeriodService, type GSTReturnPeriodPayload } from "@/services/gstReturnPeriodService";

const keys = {
  all: (companyId: string) => ["gst-return-periods", companyId] as const,
  list: (companyId: string, page: number) => ["gst-return-periods", companyId, "list", page] as const,
  detail: (companyId: string, id: string) => ["gst-return-periods", companyId, "detail", id] as const,
};

export function useGstReturnPeriods(companyId: string | undefined, page = 1) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page) : ["gst-return-periods", "none"],
    queryFn: () => gstReturnPeriodService.list(companyId as string, page),
    enabled: !!companyId,
  });
}

export function useGstReturnPeriod(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: companyId && periodId ? keys.detail(companyId, periodId) : ["gst-return-periods", "none"],
    queryFn: () => gstReturnPeriodService.get(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}

export function useCreateGstReturnPeriod(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: GSTReturnPeriodPayload) => gstReturnPeriodService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
