import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { SalesInvoice } from "@/types/accounting";

export interface SalesInvoiceItemPayload {
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

export interface SalesInvoicePayload {
  financial_year_id: string;
  customer_id: string;
  invoice_number: string;
  invoice_date: string;
  place_of_supply?: string | null;
  place_of_supply_state_code?: string | null;
  discount?: number;
  items: SalesInvoiceItemPayload[];
}

export interface SalesInvoiceFilters {
  companyId: string;
  status?: string;
  customerId?: string;
  financialYearId?: string;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}

function buildQuery(filters: SalesInvoiceFilters): string {
  const params = new URLSearchParams();
  params.set("company_id", filters.companyId);
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.pageSize ?? 20));
  if (filters.status) params.set("status", filters.status);
  if (filters.customerId) params.set("customer_id", filters.customerId);
  if (filters.financialYearId) params.set("financial_year_id", filters.financialYearId);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.search) params.set("search", filters.search);
  return params.toString();
}

export const salesInvoiceService = {
  list: (filters: SalesInvoiceFilters) =>
    apiClient.get<PaginatedData<SalesInvoice>>(`/accounting/sales-invoices?${buildQuery(filters)}`),
  get: (companyId: string, id: string) =>
    apiClient.get<SalesInvoice>(`/accounting/sales-invoices/${id}?company_id=${companyId}`),
  create: (companyId: string, payload: SalesInvoicePayload) =>
    apiClient.post<SalesInvoice>(`/accounting/sales-invoices?company_id=${companyId}`, payload),
  update: (companyId: string, id: string, payload: Partial<SalesInvoicePayload>) =>
    apiClient.patch<SalesInvoice>(`/accounting/sales-invoices/${id}?company_id=${companyId}`, payload),
  post: (companyId: string, id: string) =>
    apiClient.post<SalesInvoice>(`/accounting/sales-invoices/${id}/post?company_id=${companyId}`),
  cancel: (companyId: string, id: string) =>
    apiClient.post<SalesInvoice>(`/accounting/sales-invoices/${id}/cancel?company_id=${companyId}`),
};
