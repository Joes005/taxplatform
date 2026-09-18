import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { tdsReturnPeriodService, type TDSReturnPeriodPayload } from "@/services/tdsReturnPeriodService";

const keys = {
  all: (companyId: string) => ["tds-return-periods", companyId] as const,
  list: (companyId: string, page: number) => ["tds-return-periods", companyId, "list", page] as const,
  detail: (companyId: string, id: string) => ["tds-return-periods", companyId, "detail", id] as const,
};

export function useTdsReturnPeriods(companyId: string | undefined, page = 1) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page) : ["tds-return-periods", "none"],
    queryFn: () => tdsReturnPeriodService.list(companyId as string, page),
    enabled: !!companyId,
  });
}

export function useTdsReturnPeriod(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: companyId && periodId ? keys.detail(companyId, periodId) : ["tds-return-periods", "none"],
    queryFn: () => tdsReturnPeriodService.get(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}

export function useCreateTdsReturnPeriod(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TDSReturnPeriodPayload) => tdsReturnPeriodService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
