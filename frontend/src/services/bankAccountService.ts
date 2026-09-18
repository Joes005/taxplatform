import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { BankAccount, BankAccountType } from "@/types/bank";

export interface BankAccountPayload {
  bank_name: string;
  branch_name?: string | null;
  account_name: string;
  account_number_masked: string;
  account_type?: BankAccountType;
  ifsc_code?: string | null;
  currency?: string;
  opening_balance?: string;
  opening_balance_date: string;
  ledger_id?: string | null;
}

export const bankAccountService = {
  list: (companyId: string, page = 1, pageSize = 20, search?: string) =>
    apiClient.get<PaginatedData<BankAccount>>(
      `/bank/accounts?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (search ? `&search=${encodeURIComponent(search)}` : "")
    ),
  get: (companyId: string, accountId: string) =>
    apiClient.get<BankAccount>(`/bank/accounts/${accountId}?company_id=${companyId}`),
  create: (companyId: string, payload: BankAccountPayload) =>
    apiClient.post<BankAccount>(`/bank/accounts?company_id=${companyId}`, payload),
  update: (companyId: string, accountId: string, payload: Partial<BankAccountPayload>) =>
    apiClient.patch<BankAccount>(`/bank/accounts/${accountId}?company_id=${companyId}`, payload),
};
