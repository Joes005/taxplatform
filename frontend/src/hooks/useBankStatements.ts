import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { bankStatementService, type BankStatementPayload } from "@/services/bankStatementService";
import type { BankTransactionReconciliationStatus } from "@/types/bank";

const keys = {
  all: (companyId: string) => ["bank-statements", companyId] as const,
  list: (companyId: string, page: number, bankAccountId?: string) =>
    ["bank-statements", companyId, "list", page, bankAccountId ?? ""] as const,
  detail: (companyId: string, id: string) => ["bank-statements", companyId, "detail", id] as const,
  balance: (companyId: string, id: string) => ["bank-statements", companyId, "balance", id] as const,
  transactions: (companyId: string, id: string, page: number, status?: string) =>
    ["bank-statements", companyId, "transactions", id, page, status ?? ""] as const,
};

export function useBankStatements(companyId: string | undefined, page = 1, bankAccountId?: string) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page, bankAccountId) : ["bank-statements", "none"],
    queryFn: () => bankStatementService.list(companyId as string, page, 20, bankAccountId),
    enabled: !!companyId,
  });
}

export function useBankStatement(companyId: string | undefined, statementId: string | undefined) {
  return useQuery({
    queryKey: companyId && statementId ? keys.detail(companyId, statementId) : ["bank-statements", "none"],
    queryFn: () => bankStatementService.get(companyId as string, statementId as string),
    enabled: !!companyId && !!statementId,
  });
}

export function useBankStatementBalanceCheck(companyId: string | undefined, statementId: string | undefined) {
  return useQuery({
    queryKey: companyId && statementId ? keys.balance(companyId, statementId) : ["bank-statements", "none"],
    queryFn: () => bankStatementService.balanceCheck(companyId as string, statementId as string),
    enabled: !!companyId && !!statementId,
  });
}

export function useBankStatementTransactions(
  companyId: string | undefined,
  statementId: string | undefined,
  page = 1,
  status?: BankTransactionReconciliationStatus
) {
  return useQuery({
    queryKey: companyId && statementId ? keys.transactions(companyId, statementId, page, status) : ["bank-statements", "none"],
    queryFn: () => bankStatementService.transactions(companyId as string, statementId as string, page, 50, status),
    enabled: !!companyId && !!statementId,
  });
}

export function useCreateBankStatement(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: BankStatementPayload) => bankStatementService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useArchiveBankStatement(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (statementId: string) => bankStatementService.archive(companyId, statementId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
