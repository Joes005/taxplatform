import { apiClient } from "@/lib/api-client";
import type { IncomeTaxCreditEntry, IncomeTaxPayment, IncomeTaxSourceType } from "@/types/incomeTax";

export interface TaxPaymentPayload {
  financial_year_id: string;
  payment_date: string;
  amount: string;
  challan_number?: string;
}

export interface CreditEntryPayload {
  financial_year_id: string;
  deductor_name: string;
  deductor_tan?: string;
  section_code?: string;
  amount: string;
  certificate_reference?: string;
  source_type?: IncomeTaxSourceType;
  source_id?: string;
}

export const incomeTaxAdvanceTaxService = {
  list: (companyId: string, financialYearId: string) =>
    apiClient.get<IncomeTaxPayment[]>(
      `/income-tax/advance-tax?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  create: (companyId: string, payload: TaxPaymentPayload) =>
    apiClient.post<IncomeTaxPayment>(`/income-tax/advance-tax?company_id=${companyId}`, payload),
};

export const incomeTaxSelfAssessmentTaxService = {
  list: (companyId: string, financialYearId: string) =>
    apiClient.get<IncomeTaxPayment[]>(
      `/income-tax/self-assessment-tax?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  create: (companyId: string, payload: TaxPaymentPayload) =>
    apiClient.post<IncomeTaxPayment>(`/income-tax/self-assessment-tax?company_id=${companyId}`, payload),
};

export const incomeTaxCreditService = {
  list: (companyId: string, financialYearId: string) =>
    apiClient.get<IncomeTaxCreditEntry[]>(
      `/income-tax/credits?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  create: (companyId: string, payload: CreditEntryPayload) =>
    apiClient.post<IncomeTaxCreditEntry>(`/income-tax/credits?company_id=${companyId}`, payload),
};
