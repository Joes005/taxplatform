import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { bankMatchService } from "@/services/bankMatchService";
import type { BankMatchSourceType } from "@/types/bank";

const keys = {
  candidates: (companyId: string, transactionId: string) => ["bank-match-candidates", companyId, transactionId] as const,
  matches: (companyId: string, transactionId: string) => ["bank-matches", companyId, transactionId] as const,
};

export function useBankMatchCandidates(companyId: string | undefined, transactionId: string | undefined) {
  return useQuery({
    queryKey: companyId && transactionId ? keys.candidates(companyId, transactionId) : ["bank-match-candidates", "none"],
    queryFn: () => bankMatchService.candidates(companyId as string, transactionId as string),
    enabled: !!companyId && !!transactionId,
  });
}

export function useBankTransactionMatches(companyId: string | undefined, transactionId: string | undefined) {
  return useQuery({
    queryKey: companyId && transactionId ? keys.matches(companyId, transactionId) : ["bank-matches", "none"],
    queryFn: () => bankMatchService.matches(companyId as string, transactionId as string),
    enabled: !!companyId && !!transactionId,
  });
}

export function useCreateBankMatch(companyId: string, transactionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { source_type: BankMatchSourceType; source_id: string; matched_amount: string; notes?: string }) =>
      bankMatchService.create(companyId, transactionId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.matches(companyId, transactionId) });
      qc.invalidateQueries({ queryKey: ["bank-transactions", companyId] });
    },
  });
}

export function useReverseBankMatch(companyId: string, transactionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (matchId: string) => bankMatchService.reverse(companyId, matchId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.matches(companyId, transactionId) });
      qc.invalidateQueries({ queryKey: ["bank-transactions", companyId] });
    },
  });
}
