import { apiClient } from "@/lib/api-client";
import type {
  HousePropertyType,
  IncomeTaxExemptIncome,
  IncomeTaxHousePropertyIncome,
  IncomeTaxOtherIncome,
  IncomeTaxSalaryIncome,
  IncomeTaxSourceType,
} from "@/types/incomeTax";

export interface SalaryIncomePayload {
  financial_year_id: string;
  employer_name: string;
  gross_salary?: string;
  allowances?: string;
  perquisites?: string;
  profit_in_lieu?: string;
  standard_deduction?: string;
  professional_tax?: string;
  tds?: string;
}

export interface HousePropertyIncomePayload {
  financial_year_id: string;
  property_type: HousePropertyType;
  address?: string;
  gross_rent?: string;
  municipal_tax?: string;
  interest_on_home_loan?: string;
}

export interface OtherIncomePayload {
  financial_year_id: string;
  income_type: string;
  description?: string;
  gross_amount?: string;
  tds?: string;
  source_type?: IncomeTaxSourceType;
  source_id?: string;
}

export interface ExemptIncomePayload {
  financial_year_id: string;
  section_code: string;
  description?: string;
  amount?: string;
  source_reference?: string;
}

export const incomeTaxSalaryService = {
  list: (companyId: string, financialYearId: string) =>
    apiClient.get<IncomeTaxSalaryIncome[]>(
      `/income-tax/salary-income?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  create: (companyId: string, payload: SalaryIncomePayload) =>
    apiClient.post<IncomeTaxSalaryIncome>(`/income-tax/salary-income?company_id=${companyId}`, payload),
  update: (companyId: string, id: string, payload: Partial<SalaryIncomePayload>) =>
    apiClient.patch<IncomeTaxSalaryIncome>(`/income-tax/salary-income/${id}?company_id=${companyId}`, payload),
  delete: (companyId: string, id: string) =>
    apiClient.delete<null>(`/income-tax/salary-income/${id}?company_id=${companyId}`),
};

export const incomeTaxHousePropertyService = {
  list: (companyId: string, financialYearId: string) =>
    apiClient.get<IncomeTaxHousePropertyIncome[]>(
      `/income-tax/house-property-income?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  create: (companyId: string, payload: HousePropertyIncomePayload) =>
    apiClient.post<IncomeTaxHousePropertyIncome>(`/income-tax/house-property-income?company_id=${companyId}`, payload),
  delete: (companyId: string, id: string) =>
    apiClient.delete<null>(`/income-tax/house-property-income/${id}?company_id=${companyId}`),
};

export const incomeTaxOtherIncomeService = {
  list: (companyId: string, financialYearId: string) =>
    apiClient.get<IncomeTaxOtherIncome[]>(
      `/income-tax/other-income?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  create: (companyId: string, payload: OtherIncomePayload) =>
    apiClient.post<IncomeTaxOtherIncome>(`/income-tax/other-income?company_id=${companyId}`, payload),
  delete: (companyId: string, id: string) =>
    apiClient.delete<null>(`/income-tax/other-income/${id}?company_id=${companyId}`),
};

export const incomeTaxExemptIncomeService = {
  list: (companyId: string, financialYearId: string) =>
    apiClient.get<IncomeTaxExemptIncome[]>(
      `/income-tax/exempt-income?company_id=${companyId}&financial_year_id=${financialYearId}`
    ),
  create: (companyId: string, payload: ExemptIncomePayload) =>
    apiClient.post<IncomeTaxExemptIncome>(`/income-tax/exempt-income?company_id=${companyId}`, payload),
  delete: (companyId: string, id: string) =>
    apiClient.delete<null>(`/income-tax/exempt-income/${id}?company_id=${companyId}`),
};
