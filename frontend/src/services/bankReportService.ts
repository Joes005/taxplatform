import { apiClient } from "@/lib/api-client";
import type { MatchReportRow, UnmatchedBankTransactionRow, UnmatchedBookTransactionRow } from "@/types/bank";

export const bankReportService = {
  unmatchedBankTransactions: (companyId: string, bankAccountId: string, periodStart: string, periodEnd: string) =>
    apiClient.get<UnmatchedBankTransactionRow[]>(
      `/bank/reports/unmatched-bank-transactions?company_id=${companyId}&bank_account_id=${bankAccountId}` +
        `&period_start=${periodStart}&period_end=${periodEnd}`
    ),
  unmatchedBookTransactions: (companyId: string, ledgerId: string, periodStart: string, periodEnd: string) =>
    apiClient.get<UnmatchedBookTransactionRow[]>(
      `/bank/reports/unmatched-book-transactions?company_id=${companyId}&ledger_id=${ledgerId}` +
        `&period_start=${periodStart}&period_end=${periodEnd}`
    ),
  matches: (companyId: string, bankAccountId: string, periodStart: string, periodEnd: string) =>
    apiClient.get<MatchReportRow[]>(
      `/bank/reports/matches?company_id=${companyId}&bank_account_id=${bankAccountId}` +
        `&period_start=${periodStart}&period_end=${periodEnd}`
    ),
  exportReconciliation: (companyId: string, reconciliationId: string, format: "csv" | "xlsx") =>
    apiClient.downloadBlob(
      `/bank/reports/reconciliations/${reconciliationId}/export?company_id=${companyId}&format=${format}`
    ),
};
