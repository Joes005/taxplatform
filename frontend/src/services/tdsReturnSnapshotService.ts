import { apiClient } from "@/lib/api-client";
import type { TDSReturnSnapshot, TDSReturnType } from "@/types/tds";

const RETURN_TYPE: TDSReturnType = "FORM_26Q";

export const tdsReturnSnapshotService = {
  getLatest: (companyId: string, periodId: string, returnType: TDSReturnType = RETURN_TYPE) =>
    apiClient.get<TDSReturnSnapshot>(
      `/tds/return-periods/${periodId}/snapshots/latest?company_id=${companyId}&return_type=${returnType}`
    ),
  listVersions: (companyId: string, periodId: string, returnType: TDSReturnType = RETURN_TYPE) =>
    apiClient.get<TDSReturnSnapshot[]>(
      `/tds/return-periods/${periodId}/snapshots?company_id=${companyId}&return_type=${returnType}`
    ),
  generate: (companyId: string, periodId: string, returnType: TDSReturnType = RETURN_TYPE) =>
    apiClient.post<TDSReturnSnapshot>(
      `/tds/return-periods/${periodId}/generate?company_id=${companyId}`,
      { return_type: returnType }
    ),
  submitForReview: (companyId: string, periodId: string, returnType: TDSReturnType = RETURN_TYPE) =>
    apiClient.post<TDSReturnSnapshot>(
      `/tds/return-periods/${periodId}/submit-for-review?company_id=${companyId}`,
      { return_type: returnType }
    ),
  approve: (companyId: string, periodId: string, comment?: string, returnType: TDSReturnType = RETURN_TYPE) =>
    apiClient.post<TDSReturnSnapshot>(`/tds/return-periods/${periodId}/approve?company_id=${companyId}`, {
      return_type: returnType,
      comment,
    }),
  requestChanges: (companyId: string, periodId: string, comment?: string, returnType: TDSReturnType = RETURN_TYPE) =>
    apiClient.post<TDSReturnSnapshot>(
      `/tds/return-periods/${periodId}/request-changes?company_id=${companyId}`,
      { return_type: returnType, comment }
    ),
  finalize: (companyId: string, periodId: string, returnType: TDSReturnType = RETURN_TYPE) =>
    apiClient.post<TDSReturnSnapshot>(
      `/tds/return-periods/${periodId}/finalize?company_id=${companyId}`,
      { return_type: returnType }
    ),
};
