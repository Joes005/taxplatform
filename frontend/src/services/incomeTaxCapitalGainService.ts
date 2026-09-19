import { apiClient } from "@/lib/api-client";
import type { CapitalAssetType, CapitalGainType, IncomeTaxCapitalGain } from "@/types/incomeTax";

export interface CapitalGainPayload {
  financial_year_id: string;
  asset_type: CapitalAssetType;
  asset_description: string;
  purchase_date: string;
  sale_date: string;
  purchase_cost?: string;
  improvement_cost?: string;
  sale_consideration?: string;
  transfer_expenses?: string;
  indexed_cost?: string;
  gain_type: CapitalGainType;
}

export const incomeTaxCapitalGainService = {
  list: (companyId: string, financialYearId: string) =>
    apiClient.get<IncomeTaxCapitalGain[]>(
      `/income-tax/capital-gains?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  create: (companyId: string, payload: CapitalGainPayload) =>
    apiClient.post<IncomeTaxCapitalGain>(`/income-tax/capital-gains?company_id=${companyId}`, payload),
  delete: (companyId: string, id: string) =>
    apiClient.delete<null>(`/income-tax/capital-gains/${id}?company_id=${companyId}`),
};
