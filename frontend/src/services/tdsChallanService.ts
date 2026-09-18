import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { TDSChallan, TDSChallanAllocation, TDSChallanStatus } from "@/types/tds";

export interface TDSChallanPayload {
  challan_number: string;
  challan_date: string;
  amount: string;
  financial_year_id: string;
  bank_reference_number?: string | null;
  notes?: string | null;
}

export const tdsChallanService = {
  list: (companyId: string, page = 1, pageSize = 20, financialYearId?: string) =>
    apiClient.get<PaginatedData<TDSChallan>>(
      `/tds/challans?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (financialYearId ? `&financial_year_id=${financialYearId}` : "")
    ),
  get: (companyId: string, challanId: string) =>
    apiClient.get<TDSChallan>(`/tds/challans/${challanId}?company_id=${companyId}`),
  create: (companyId: string, payload: TDSChallanPayload) =>
    apiClient.post<TDSChallan>(`/tds/challans?company_id=${companyId}`, payload),
  updateStatus: (companyId: string, challanId: string, status: TDSChallanStatus) =>
    apiClient.patch<TDSChallan>(`/tds/challans/${challanId}?company_id=${companyId}`, { status }),
  update: (
    companyId: string,
    challanId: string,
    payload: Partial<Omit<TDSChallanPayload, "financial_year_id">>
  ) => apiClient.patch<TDSChallan>(`/tds/challans/${challanId}?company_id=${companyId}`, payload),
  allocate: (companyId: string, challanId: string, tdsTransactionId: string, allocatedAmount: string) =>
    apiClient.post<TDSChallanAllocation>(`/tds/challans/${challanId}/allocate?company_id=${companyId}`, {
      tds_transaction_id: tdsTransactionId,
      allocated_amount: allocatedAmount,
    }),
};
