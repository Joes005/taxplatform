import { apiClient } from "@/lib/api-client";
import type { BankMatchCandidate, BankMatchSourceType, BankTransactionMatch } from "@/types/bank";

export const bankMatchService = {
  candidates: (companyId: string, transactionId: string) =>
    apiClient.get<BankMatchCandidate[]>(`/bank/transactions/${transactionId}/candidates?company_id=${companyId}`),
  matches: (companyId: string, transactionId: string) =>
    apiClient.get<BankTransactionMatch[]>(`/bank/transactions/${transactionId}/matches?company_id=${companyId}`),
  create: (
    companyId: string,
    transactionId: string,
    payload: { source_type: BankMatchSourceType; source_id: string; matched_amount: string; notes?: string }
  ) => apiClient.post<BankTransactionMatch>(`/bank/transactions/${transactionId}/match?company_id=${companyId}`, payload),
  reverse: (companyId: string, matchId: string) =>
    apiClient.post<BankTransactionMatch>(`/bank/matches/${matchId}/reverse?company_id=${companyId}`),
};
