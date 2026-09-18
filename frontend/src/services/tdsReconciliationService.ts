import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { TDSPaymentReconciliation } from "@/types/tds";

export const tdsReconciliationService = {
  run: (companyId: string, financialYearId: string) =>
    apiClient.post<TDSPaymentReconciliation[]>(
      `/tds/reconciliation/run?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  list: (companyId: string, financialYearId?: string, page = 1, pageSize = 50) =>
    apiClient.get<PaginatedData<TDSPaymentReconciliation>>(
      `/tds/reconciliation?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (financialYearId ? `&financial_year_id=${financialYearId}` : "")
    ),
};
