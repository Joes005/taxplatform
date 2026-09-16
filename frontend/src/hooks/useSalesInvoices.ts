import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  salesInvoiceService,
  type SalesInvoiceFilters,
  type SalesInvoicePayload,
} from "@/services/salesInvoiceService";

// Hierarchical keys, same lesson as Phase 2's useDocuments: a mutation
// invalidating ["sales-invoices", companyId] must actually be a prefix of
// the list query's key, or the visible list silently goes stale.
const keys = {
  all: (companyId: string) => ["sales-invoices", companyId] as const,
  list: (filters: SalesInvoiceFilters) => ["sales-invoices", filters.companyId, "list", filters] as const,
  detail: (companyId: string, id: string) => ["sales-invoices", companyId, "detail", id] as const,
};

export function useSalesInvoices(filters: SalesInvoiceFilters | null) {
  return useQuery({
    queryKey: filters ? keys.list(filters) : ["sales-invoices", "none"],
    queryFn: () => salesInvoiceService.list(filters as SalesInvoiceFilters),
    enabled: !!filters?.companyId,
  });
}

export function useSalesInvoice(companyId: string | undefined, id: string | undefined) {
  return useQuery({
    queryKey: companyId && id ? keys.detail(companyId, id) : ["sales-invoices", "none"],
    queryFn: () => salesInvoiceService.get(companyId as string, id as string),
    enabled: !!companyId && !!id,
  });
}

export function useCreateSalesInvoice(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SalesInvoicePayload) => salesInvoiceService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function usePostSalesInvoice(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesInvoiceService.post(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useCancelSalesInvoice(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesInvoiceService.cancel(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
