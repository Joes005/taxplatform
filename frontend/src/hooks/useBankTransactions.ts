import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { bankTransactionService } from "@/services/bankTransactionService";
import type { BankTransactionReconciliationStatus } from "@/types/bank";

const keys = {
  all: (companyId: string) => ["bank-transactions", companyId] as const,
  list: (companyId: string, page: number, status?: string) =>
    ["bank-transactions", companyId, "list", page, status ?? ""] as const,
  detail: (companyId: string, id: string) => ["bank-transactions", companyId, "detail", id] as const,
};

export function useBankTransactions(
  companyId: string | undefined,
  page = 1,
  filters?: { bankAccountId?: string; reconciliationStatus?: BankTransactionReconciliationStatus; search?: string }
) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page, filters?.reconciliationStatus) : ["bank-transactions", "none"],
    queryFn: () => bankTransactionService.list(companyId as string, page, 50, filters),
    enabled: !!companyId,
  });
}

export function useBankTransaction(companyId: string | undefined, transactionId: string | undefined) {
  return useQuery({
    queryKey: companyId && transactionId ? keys.detail(companyId, transactionId) : ["bank-transactions", "none"],
    queryFn: () => bankTransactionService.get(companyId as string, transactionId as string),
    enabled: !!companyId && !!transactionId,
  });
}

export function useExcludeBankTransaction(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (transactionId: string) => bankTransactionService.exclude(companyId, transactionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useFlagBankTransactionForReview(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (transactionId: string) => bankTransactionService.flagForReview(companyId, transactionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useCreateBankAdjustment(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      transactionId,
      payload,
    }: {
      transactionId: string;
      payload: { financial_year_id: string; journal_number: string; offset_ledger_id: string; narration?: string };
    }) => bankTransactionService.createAdjustment(companyId, transactionId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
