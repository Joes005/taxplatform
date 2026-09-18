import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { bankReconciliationService, type BankReconciliationPayload } from "@/services/bankReconciliationService";

const keys = {
  all: (companyId: string) => ["bank-reconciliations", companyId] as const,
  list: (companyId: string, page: number) => ["bank-reconciliations", companyId, "list", page] as const,
  detail: (companyId: string, id: string) => ["bank-reconciliations", companyId, "detail", id] as const,
  summary: (companyId: string, id: string) => ["bank-reconciliations", companyId, "summary", id] as const,
};

export function useBankReconciliations(companyId: string | undefined, page = 1, bankAccountId?: string) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page) : ["bank-reconciliations", "none"],
    queryFn: () => bankReconciliationService.list(companyId as string, page, 20, bankAccountId),
    enabled: !!companyId,
  });
}

export function useBankReconciliation(companyId: string | undefined, reconciliationId: string | undefined) {
  return useQuery({
    queryKey: companyId && reconciliationId ? keys.detail(companyId, reconciliationId) : ["bank-reconciliations", "none"],
    queryFn: () => bankReconciliationService.get(companyId as string, reconciliationId as string),
    enabled: !!companyId && !!reconciliationId,
  });
}

export function useBankReconciliationSummary(companyId: string | undefined, reconciliationId: string | undefined) {
  return useQuery({
    queryKey: companyId && reconciliationId ? keys.summary(companyId, reconciliationId) : ["bank-reconciliations", "none"],
    queryFn: () => bankReconciliationService.summary(companyId as string, reconciliationId as string),
    enabled: !!companyId && !!reconciliationId,
  });
}

export function useStartBankReconciliation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: BankReconciliationPayload) => bankReconciliationService.start(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

function useReconciliationAction(
  companyId: string,
  reconciliationId: string,
  fn: (companyId: string, reconciliationId: string) => Promise<unknown>
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => fn(companyId, reconciliationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, reconciliationId) });
      qc.invalidateQueries({ queryKey: keys.summary(companyId, reconciliationId) });
      qc.invalidateQueries({ queryKey: ["bank-transactions", companyId] });
    },
  });
}

export function useRunBankMatching(companyId: string, reconciliationId: string) {
  return useReconciliationAction(companyId, reconciliationId, bankReconciliationService.runMatching);
}
export function useSubmitBankReconciliation(companyId: string, reconciliationId: string) {
  return useReconciliationAction(companyId, reconciliationId, bankReconciliationService.submit);
}
export function useApproveBankReconciliation(companyId: string, reconciliationId: string) {
  return useReconciliationAction(companyId, reconciliationId, (c, r) => bankReconciliationService.approve(c, r));
}
export function useRejectBankReconciliation(companyId: string, reconciliationId: string) {
  return useReconciliationAction(companyId, reconciliationId, (c, r) => bankReconciliationService.reject(c, r));
}
export function useLockBankReconciliation(companyId: string, reconciliationId: string) {
  return useReconciliationAction(companyId, reconciliationId, bankReconciliationService.lock);
}
export function useCancelBankReconciliation(companyId: string, reconciliationId: string) {
  return useReconciliationAction(companyId, reconciliationId, bankReconciliationService.cancel);
}
