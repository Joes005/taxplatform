import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { tdsTransactionService, type TDSTransactionPayload } from "@/services/tdsTransactionService";
import type { TDSTransactionStatus } from "@/types/tds";

const keys = {
  all: (companyId: string) => ["tds-transactions", companyId] as const,
  list: (companyId: string, page: number, status?: string) =>
    ["tds-transactions", companyId, "list", page, status ?? ""] as const,
  detail: (companyId: string, id: string) => ["tds-transactions", companyId, "detail", id] as const,
  payable: (companyId: string) => ["tds-transactions", companyId, "payable"] as const,
};

export function useTdsTransactions(
  companyId: string | undefined,
  page = 1,
  status?: TDSTransactionStatus
) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page, status) : ["tds-transactions", "none"],
    queryFn: () => tdsTransactionService.list(companyId as string, page, 20, { status }),
    enabled: !!companyId,
  });
}

export function useTdsTransaction(companyId: string | undefined, transactionId: string | undefined) {
  return useQuery({
    queryKey: companyId && transactionId ? keys.detail(companyId, transactionId) : ["tds-transactions", "none"],
    queryFn: () => tdsTransactionService.get(companyId as string, transactionId as string),
    enabled: !!companyId && !!transactionId,
  });
}

export function useTdsPayableSummary(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? keys.payable(companyId) : ["tds-transactions", "none"],
    queryFn: () => tdsTransactionService.payableSummary(companyId as string),
    enabled: !!companyId,
  });
}

export function useCreateTdsTransaction(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TDSTransactionPayload) => tdsTransactionService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useCalculateTdsTransaction(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (transactionId: string) => tdsTransactionService.calculate(companyId, transactionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useOverrideTdsTransaction(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, tdsAmount, reason }: { id: string; tdsAmount: string; reason: string }) =>
      tdsTransactionService.override(companyId, id, tdsAmount, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useDeductTdsTransaction(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (transactionId: string) => tdsTransactionService.deduct(companyId, transactionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useCancelTdsTransaction(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (transactionId: string) => tdsTransactionService.cancel(companyId, transactionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
