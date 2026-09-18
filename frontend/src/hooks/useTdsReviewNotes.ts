import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { tdsReviewNoteService, type TDSReviewNoteCreatePayload } from "@/services/tdsReviewNoteService";

const keys = {
  list: (companyId: string, periodId: string) => ["tds-review-notes", companyId, periodId] as const,
};

export function useTdsReviewNotes(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: companyId && periodId ? keys.list(companyId, periodId) : ["tds-review-notes", "none"],
    queryFn: () => tdsReviewNoteService.list(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}

export function useCreateTdsReviewNote(companyId: string, periodId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TDSReviewNoteCreatePayload) => tdsReviewNoteService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list(companyId, periodId) }),
  });
}

export function useResolveTdsReviewNote(companyId: string, periodId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (noteId: string) => tdsReviewNoteService.resolve(companyId, noteId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list(companyId, periodId) }),
  });
}
