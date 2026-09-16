import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  accountingPeriodService,
  customerService,
  financialYearService,
  ledgerService,
  productService,
  vendorService,
  type AccountingPeriodPayload,
  type CustomerPayload,
  type FinancialYearPayload,
  type LedgerPayload,
  type ProductPayload,
  type VendorPayload,
} from "@/services/accountingMasterDataService";
import type { PeriodStatus } from "@/types/accounting";

// --- Financial Years ---
export function useFinancialYears(companyId: string | undefined) {
  return useQuery({
    queryKey: ["financial-years", companyId],
    queryFn: () => financialYearService.list(companyId as string),
    enabled: !!companyId,
  });
}

export function useCreateFinancialYear(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: FinancialYearPayload) => financialYearService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["financial-years", companyId] }),
  });
}

export function useUpdateFinancialYear(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<FinancialYearPayload & { status: string }> }) =>
      financialYearService.update(companyId, id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["financial-years", companyId] }),
  });
}

// --- Accounting Periods ---
export function useAccountingPeriods(companyId: string | undefined, financialYearId?: string) {
  return useQuery({
    queryKey: ["accounting-periods", companyId, financialYearId],
    queryFn: () => accountingPeriodService.list(companyId as string, financialYearId),
    enabled: !!companyId,
  });
}

export function useCreatePeriod(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AccountingPeriodPayload) => accountingPeriodService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounting-periods", companyId] }),
  });
}

export function useUpdatePeriodStatus(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: PeriodStatus }) =>
      accountingPeriodService.updateStatus(companyId, id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounting-periods", companyId] }),
  });
}

// --- Ledgers ---
export function useLedgers(companyId: string | undefined, search?: string) {
  return useQuery({
    queryKey: ["ledgers", companyId, search],
    queryFn: () => ledgerService.list(companyId as string, 1, 100, search),
    enabled: !!companyId,
  });
}

export function useCreateLedger(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: LedgerPayload) => ledgerService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ledgers", companyId] }),
  });
}

export function useUpdateLedger(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<LedgerPayload> }) =>
      ledgerService.update(companyId, id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ledgers", companyId] }),
  });
}

// --- Customers ---
export function useCustomers(companyId: string | undefined, search?: string) {
  return useQuery({
    queryKey: ["customers", companyId, search],
    queryFn: () => customerService.list(companyId as string, 1, 100, search),
    enabled: !!companyId,
  });
}

export function useCreateCustomer(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CustomerPayload) => customerService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["customers", companyId] }),
  });
}

export function useUpdateCustomer(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<CustomerPayload> }) =>
      customerService.update(companyId, id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["customers", companyId] }),
  });
}

// --- Vendors ---
export function useVendors(companyId: string | undefined, search?: string) {
  return useQuery({
    queryKey: ["vendors", companyId, search],
    queryFn: () => vendorService.list(companyId as string, 1, 100, search),
    enabled: !!companyId,
  });
}

export function useCreateVendor(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: VendorPayload) => vendorService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vendors", companyId] }),
  });
}

export function useUpdateVendor(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<VendorPayload> }) =>
      vendorService.update(companyId, id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vendors", companyId] }),
  });
}

// --- Products ---
export function useProducts(companyId: string | undefined, search?: string) {
  return useQuery({
    queryKey: ["products", companyId, search],
    queryFn: () => productService.list(companyId as string, 1, 100, search),
    enabled: !!companyId,
  });
}

export function useCreateProduct(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductPayload) => productService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["products", companyId] }),
  });
}

export function useUpdateProduct(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ProductPayload> }) =>
      productService.update(companyId, id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["products", companyId] }),
  });
}
