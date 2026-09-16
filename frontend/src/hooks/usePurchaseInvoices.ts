import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  purchaseInvoiceService,
  type PurchaseInvoiceFilters,
  type PurchaseInvoicePayload,
} from "@/services/purchaseInvoiceService";

const keys = {
  all: (companyId: string) => ["purchase-invoices", companyId] as const,
  list: (filters: PurchaseInvoiceFilters) =>
    ["purchase-invoices", filters.companyId, "list", filters] as const,
  detail: (companyId: string, id: string) => ["purchase-invoices", companyId, "detail", id] as const,
};

export function usePurchaseInvoices(filters: PurchaseInvoiceFilters | null) {
  return useQuery({
    queryKey: filters ? keys.list(filters) : ["purchase-invoices", "none"],
    queryFn: () => purchaseInvoiceService.list(filters as PurchaseInvoiceFilters),
    enabled: !!filters?.companyId,
  });
}

export function usePurchaseInvoice(companyId: string | undefined, id: string | undefined) {
  return useQuery({
    queryKey: companyId && id ? keys.detail(companyId, id) : ["purchase-invoices", "none"],
    queryFn: () => purchaseInvoiceService.get(companyId as string, id as string),
    enabled: !!companyId && !!id,
  });
}

export function useCreatePurchaseInvoice(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PurchaseInvoicePayload) => purchaseInvoiceService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function usePostPurchaseInvoice(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => purchaseInvoiceService.post(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useCancelPurchaseInvoice(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => purchaseInvoiceService.cancel(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
