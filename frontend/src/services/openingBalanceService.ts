import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { BalanceType, OpeningBalanceAccountType } from "@/types/accounting";

export interface OpeningBalance {
  id: string;
  financial_year_id: string;
  account_type: OpeningBalanceAccountType;
  account_id: string;
  amount: string;
  balance_type: BalanceType;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface OpeningBalanceCreatePayload {
  financial_year_id: string;
  account_type: OpeningBalanceAccountType;
  account_id: string;
  amount: number | string;
  balance_type: BalanceType;
  notes?: string | null;
}

export const openingBalanceService = {
  list: (
    companyId: string,
    params?: {
      financialYearId?: string;
      accountType?: OpeningBalanceAccountType;
      page?: number;
      pageSize?: number;
    }
  ) => {
    const qs = new URLSearchParams({ company_id: companyId });
    if (params?.financialYearId) qs.set("financial_year_id", params.financialYearId);
    if (params?.accountType) qs.set("account_type", params.accountType);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.pageSize) qs.set("page_size", String(params.pageSize));
    return apiClient.get<PaginatedData<OpeningBalance>>(`/accounting/opening-balances?${qs.toString()}`);
  },

  create: (companyId: string, payload: OpeningBalanceCreatePayload) =>
    apiClient.post<OpeningBalance>(`/accounting/opening-balances?company_id=${companyId}`, payload),
};
