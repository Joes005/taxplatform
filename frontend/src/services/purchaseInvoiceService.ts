import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { PurchaseInvoice } from "@/types/accounting";

export interface PurchaseInvoiceItemPayload {
  product_service_id?: string | null;
  description?: string | null;
  quantity: number;
  unit?: string | null;
  unit_price: number;
  discount?: number;
  cgst_rate?: number;
  sgst_rate?: number;
  igst_rate?: number;
  cess_rate?: number;
}

export interface PurchaseInvoicePayload {
  financial_year_id: string;
  vendor_id: string;
  invoice_number: string;
  invoice_date: string;
  supplier_invoice_number?: string | null;
  supplier_invoice_date?: string | null;
  place_of_supply?: string | null;
  discount?: number;
  items: PurchaseInvoiceItemPayload[];
}

export interface PurchaseInvoiceFilters {
  companyId: string;
  status?: string;
  vendorId?: string;
  financialYearId?: string;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}

function buildQuery(filters: PurchaseInvoiceFilters): string {
  const params = new URLSearchParams();
  params.set("company_id", filters.companyId);
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.pageSize ?? 20));
  if (filters.status) params.set("status", filters.status);
  if (filters.vendorId) params.set("vendor_id", filters.vendorId);
  if (filters.financialYearId) params.set("financial_year_id", filters.financialYearId);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.search) params.set("search", filters.search);
  return params.toString();
}

export const purchaseInvoiceService = {
  list: (filters: PurchaseInvoiceFilters) =>
    apiClient.get<PaginatedData<PurchaseInvoice>>(`/accounting/purchase-invoices?${buildQuery(filters)}`),
  get: (companyId: string, id: string) =>
    apiClient.get<PurchaseInvoice>(`/accounting/purchase-invoices/${id}?company_id=${companyId}`),
  create: (companyId: string, payload: PurchaseInvoicePayload) =>
    apiClient.post<PurchaseInvoice>(`/accounting/purchase-invoices?company_id=${companyId}`, payload),
  update: (companyId: string, id: string, payload: Partial<PurchaseInvoicePayload>) =>
    apiClient.patch<PurchaseInvoice>(`/accounting/purchase-invoices/${id}?company_id=${companyId}`, payload),
  post: (companyId: string, id: string) =>
    apiClient.post<PurchaseInvoice>(`/accounting/purchase-invoices/${id}/post?company_id=${companyId}`),
  cancel: (companyId: string, id: string) =>
    apiClient.post<PurchaseInvoice>(`/accounting/purchase-invoices/${id}/cancel?company_id=${companyId}`),
};
