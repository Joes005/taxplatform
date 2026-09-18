import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { bankAccountService, type BankAccountPayload } from "@/services/bankAccountService";

const keys = {
  all: (companyId: string) => ["bank-accounts", companyId] as const,
  list: (companyId: string, page: number, search?: string) =>
    ["bank-accounts", companyId, "list", page, search ?? ""] as const,
  detail: (companyId: string, id: string) => ["bank-accounts", companyId, "detail", id] as const,
};

export function useBankAccounts(companyId: string | undefined, page = 1, search?: string) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page, search) : ["bank-accounts", "none"],
    queryFn: () => bankAccountService.list(companyId as string, page, 20, search),
    enabled: !!companyId,
  });
}

export function useBankAccount(companyId: string | undefined, accountId: string | undefined) {
  return useQuery({
    queryKey: companyId && accountId ? keys.detail(companyId, accountId) : ["bank-accounts", "none"],
    queryFn: () => bankAccountService.get(companyId as string, accountId as string),
    enabled: !!companyId && !!accountId,
  });
}

export function useCreateBankAccount(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: BankAccountPayload) => bankAccountService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useUpdateBankAccount(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<BankAccountPayload> }) =>
      bankAccountService.update(companyId, id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
