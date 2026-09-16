import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { itcService } from "@/services/itcService";

const keys = {
  all: (companyId: string, periodId: string) => ["itc", companyId, periodId] as const,
  summary: (companyId: string, periodId: string) => ["itc", companyId, periodId, "summary"] as const,
  list: (companyId: string, periodId: string, category?: string) =>
    ["itc", companyId, periodId, "list", category] as const,
};

export function useItcSummary(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: companyId && periodId ? keys.summary(companyId, periodId) : ["itc", "none"],
    queryFn: () => itcService.summary(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
    retry: false,
  });
}

export function useItcResults(
  companyId: string | undefined,
  periodId: string | undefined,
  category?: string
) {
  return useQuery({
    queryKey: companyId && periodId ? keys.list(companyId, periodId, category) : ["itc", "none"],
    queryFn: () => itcService.list(companyId as string, periodId as string, { category }),
    enabled: !!companyId && !!periodId,
  });
}

export function useReviewItc(companyId: string, periodId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ resultId, comment }: { resultId: string; comment?: string }) =>
      itcService.review(companyId, periodId, resultId, comment),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId, periodId) }),
  });
}

export function useApproveItc(companyId: string, periodId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ resultId, approved, comment }: { resultId: string; approved: boolean; comment?: string }) =>
      itcService.approve(companyId, periodId, resultId, approved, comment),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId, periodId) }),
  });
}
