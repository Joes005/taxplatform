import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { TDSQuarter, TDSReturnPeriod } from "@/types/tds";

export interface TDSReturnPeriodPayload {
  financial_year_id: string;
  quarter: TDSQuarter;
}

export const tdsReturnPeriodService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<TDSReturnPeriod>>(
      `/tds/return-periods?company_id=${companyId}&page=${page}&page_size=${pageSize}`
    ),
  get: (companyId: string, periodId: string) =>
    apiClient.get<TDSReturnPeriod>(`/tds/return-periods/${periodId}?company_id=${companyId}`),
  create: (companyId: string, payload: TDSReturnPeriodPayload) =>
    apiClient.post<TDSReturnPeriod>(`/tds/return-periods?company_id=${companyId}`, payload),
};
