import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  openingBalanceService,
  type OpeningBalanceCreatePayload,
} from "@/services/openingBalanceService";
import type { OpeningBalanceAccountType } from "@/types/accounting";

export function useOpeningBalances(
  companyId: string,
  params?: {
    financialYearId?: string;
    accountType?: OpeningBalanceAccountType;
    page?: number;
    pageSize?: number;
  }
) {
  return useQuery({
    queryKey: ["opening-balances", companyId, params],
    queryFn: () => openingBalanceService.list(companyId, params),
    enabled: !!companyId,
  });
}

export function useCreateOpeningBalance(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OpeningBalanceCreatePayload) =>
      openingBalanceService.create(companyId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opening-balances", companyId] });
      queryClient.invalidateQueries({ queryKey: ["ledgers", companyId] });
      queryClient.invalidateQueries({ queryKey: ["reports", companyId] });
    },
  });
}
