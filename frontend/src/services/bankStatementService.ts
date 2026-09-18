import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { BankStatement, BankStatementBalanceCheck, BankStatementSourceType, BankTransaction, BankTransactionReconciliationStatus } from "@/types/bank";

export interface BankStatementPayload {
  bank_account_id: string;
  statement_name: string;
  period_start: string;
  period_end: string;
  opening_balance: string;
  closing_balance: string;
  source_type?: BankStatementSourceType;
}

export const bankStatementService = {
  list: (companyId: string, page = 1, pageSize = 20, bankAccountId?: string) =>
    apiClient.get<PaginatedData<BankStatement>>(
      `/bank/statements?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (bankAccountId ? `&bank_account_id=${bankAccountId}` : "")
    ),
  get: (companyId: string, statementId: string) =>
    apiClient.get<BankStatement>(`/bank/statements/${statementId}?company_id=${companyId}`),
  create: (companyId: string, payload: BankStatementPayload) =>
    apiClient.post<BankStatement>(`/bank/statements?company_id=${companyId}`, payload),
  archive: (companyId: string, statementId: string) =>
    apiClient.post<BankStatement>(`/bank/statements/${statementId}/archive?company_id=${companyId}`),
  balanceCheck: (companyId: string, statementId: string) =>
    apiClient.get<BankStatementBalanceCheck>(`/bank/statements/${statementId}/balance-check?company_id=${companyId}`),
  transactions: (
    companyId: string,
    statementId: string,
    page = 1,
    pageSize = 50,
    reconciliationStatus?: BankTransactionReconciliationStatus
  ) =>
    apiClient.get<PaginatedData<BankTransaction>>(
      `/bank/statements/${statementId}/transactions?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (reconciliationStatus ? `&reconciliation_status=${reconciliationStatus}` : "")
    ),
};
