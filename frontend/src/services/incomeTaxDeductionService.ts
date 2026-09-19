import { apiClient } from "@/lib/api-client";
import type { BusinessIncomePreview, IncomeTaxDeduction, LedgerTaxClassification } from "@/types/incomeTax";

export interface DeductionPayload {
  financial_year_id: string;
  section_code: string;
  description?: string;
  claimed_amount?: string;
}

export const incomeTaxDeductionService = {
  list: (companyId: string, financialYearId: string) =>
    apiClient.get<IncomeTaxDeduction[]>(
      `/income-tax/deductions?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  create: (companyId: string, payload: DeductionPayload) =>
    apiClient.post<IncomeTaxDeduction>(`/income-tax/deductions?company_id=${companyId}`, payload),
  delete: (companyId: string, id: string) =>
    apiClient.delete<null>(`/income-tax/deductions/${id}?company_id=${companyId}`),
};

export const incomeTaxLedgerClassificationService = {
  set: (companyId: string, ledgerId: string, classification: LedgerTaxClassification, notes?: string) =>
    apiClient.post<null>(`/income-tax/ledger-classifications?company_id=${companyId}`, {
      ledger_id: ledgerId,
      classification,
      notes,
    }),
};

export const businessIncomePreviewService = {
  preview: (companyId: string, financialYearId: string) =>
    apiClient.get<BusinessIncomePreview>(
      `/income-tax/business-income-preview?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
};
