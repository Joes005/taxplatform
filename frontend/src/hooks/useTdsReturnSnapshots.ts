import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { tdsReturnSnapshotService } from "@/services/tdsReturnSnapshotService";

const keys = {
  latest: (companyId: string, periodId: string) => ["tds-return-snapshot", companyId, periodId, "latest"] as const,
  versions: (companyId: string, periodId: string) => ["tds-return-snapshot", companyId, periodId, "versions"] as const,
};

export function useLatestTdsReturnSnapshot(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: companyId && periodId ? keys.latest(companyId, periodId) : ["tds-return-snapshot", "none"],
    queryFn: () => tdsReturnSnapshotService.getLatest(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
    retry: false,
  });
}

export function useTdsReturnSnapshotVersions(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: companyId && periodId ? keys.versions(companyId, periodId) : ["tds-return-snapshot", "none"],
    queryFn: () => tdsReturnSnapshotService.listVersions(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}

function useSnapshotMutation(
  companyId: string,
  periodId: string,
  fn: (companyId: string, periodId: string) => Promise<unknown>
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => fn(companyId, periodId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.latest(companyId, periodId) });
      qc.invalidateQueries({ queryKey: keys.versions(companyId, periodId) });
      qc.invalidateQueries({ queryKey: ["tds-return-periods", companyId] });
    },
  });
}

export function useGenerateTdsReturnSnapshot(companyId: string, periodId: string) {
  return useSnapshotMutation(companyId, periodId, tdsReturnSnapshotService.generate);
}

export function useSubmitTdsReturnForReview(companyId: string, periodId: string) {
  return useSnapshotMutation(companyId, periodId, tdsReturnSnapshotService.submitForReview);
}

export function useApproveTdsReturn(companyId: string, periodId: string) {
  return useSnapshotMutation(companyId, periodId, (c, p) => tdsReturnSnapshotService.approve(c, p));
}

export function useRequestTdsReturnChanges(companyId: string, periodId: string) {
  return useSnapshotMutation(companyId, periodId, (c, p) => tdsReturnSnapshotService.requestChanges(c, p));
}

export function useFinalizeTdsReturn(companyId: string, periodId: string) {
  return useSnapshotMutation(companyId, periodId, tdsReturnSnapshotService.finalize);
}
