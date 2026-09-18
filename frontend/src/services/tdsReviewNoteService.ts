import { apiClient } from "@/lib/api-client";
import type { TDSReviewNote } from "@/types/tds";

export interface TDSReviewNoteCreatePayload {
  return_period_id: string;
  entity_type: string;
  entity_id: string;
  note: string;
}

export const tdsReviewNoteService = {
  list: (companyId: string, returnPeriodId: string) =>
    apiClient.get<TDSReviewNote[]>(
      `/tds/review-notes?company_id=${companyId}&return_period_id=${returnPeriodId}`
    ),
  create: (companyId: string, payload: TDSReviewNoteCreatePayload) =>
    apiClient.post<TDSReviewNote>(`/tds/review-notes?company_id=${companyId}`, payload),
  resolve: (companyId: string, noteId: string) =>
    apiClient.post<TDSReviewNote>(`/tds/review-notes/${noteId}/resolve?company_id=${companyId}`),
};
