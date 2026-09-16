// Financial Years, Periods, Ledgers, Customers, Vendors, Products —
// grouped in one file since each is a thin CRUD wrapper of identical
// shape (unlike Sales/Purchase Invoices, Imports, etc., which have real
// business-flow methods and get their own files).
import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type {
  AccountingPeriod,
  Customer,
  FinancialYear,
  Ledger,
  PeriodStatus,
  ProductServiceItem,
  Vendor,
} from "@/types/accounting";

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  return search.toString();
}

export interface FinancialYearPayload {
  name: string;
  start_date: string;
  end_date: string;
  is_current?: boolean;
}

export const financialYearService = {
  list: (companyId: string, page = 1, pageSize = 50) =>
    apiClient.get<PaginatedData<FinancialYear>>(
      `/accounting/financial-years?${qs({ company_id: companyId, page, page_size: pageSize })}`
    ),
  create: (companyId: string, payload: FinancialYearPayload) =>
    apiClient.post<FinancialYear>(`/accounting/financial-years?company_id=${companyId}`, payload),
  update: (companyId: string, id: string, payload: Partial<FinancialYearPayload & { status: string }>) =>
    apiClient.patch<FinancialYear>(
      `/accounting/financial-years/${id}?company_id=${companyId}`,
      payload
    ),
};

export interface AccountingPeriodPayload {
  financial_year_id: string;
  name: string;
  start_date: string;
  end_date: string;
}

export const accountingPeriodService = {
  list: (companyId: string, financialYearId?: string) =>
    apiClient.get<PaginatedData<AccountingPeriod>>(
      `/accounting/periods?${qs({ company_id: companyId, financial_year_id: financialYearId, page_size: 100 })}`
    ),
  create: (companyId: string, payload: AccountingPeriodPayload) =>
    apiClient.post<AccountingPeriod>(`/accounting/periods?company_id=${companyId}`, payload),
  updateStatus: (companyId: string, id: string, status: PeriodStatus) =>
    apiClient.patch<AccountingPeriod>(`/accounting/periods/${id}?company_id=${companyId}`, { status }),
};

export interface LedgerPayload {
  name: string;
  code?: string | null;
  ledger_type: string;
  parent_ledger_id?: string | null;
  opening_balance?: string;
  opening_balance_type?: string;
}

export const ledgerService = {
  list: (companyId: string, page = 1, pageSize = 50, search?: string) =>
    apiClient.get<PaginatedData<Ledger>>(
      `/accounting/ledgers?${qs({ company_id: companyId, page, page_size: pageSize, search })}`
    ),
  create: (companyId: string, payload: LedgerPayload) =>
    apiClient.post<Ledger>(`/accounting/ledgers?company_id=${companyId}`, payload),
  update: (companyId: string, id: string, payload: Partial<LedgerPayload & { is_active: boolean }>) =>
    apiClient.patch<Ledger>(`/accounting/ledgers/${id}?company_id=${companyId}`, payload),
};

export interface CustomerPayload {
  name: string;
  code?: string | null;
  gstin?: string | null;
  pan?: string | null;
  email?: string | null;
  phone?: string | null;
  billing_address?: string | null;
  shipping_address?: string | null;
  state?: string | null;
  state_code?: string | null;
  pincode?: string | null;
}

export const customerService = {
  list: (companyId: string, page = 1, pageSize = 50, search?: string) =>
    apiClient.get<PaginatedData<Customer>>(
      `/accounting/customers?${qs({ company_id: companyId, page, page_size: pageSize, search })}`
    ),
  create: (companyId: string, payload: CustomerPayload) =>
    apiClient.post<Customer>(`/accounting/customers?company_id=${companyId}`, payload),
  update: (companyId: string, id: string, payload: Partial<CustomerPayload & { is_active: boolean }>) =>
    apiClient.patch<Customer>(`/accounting/customers/${id}?company_id=${companyId}`, payload),
};

export interface VendorPayload {
  name: string;
  code?: string | null;
  gstin?: string | null;
  pan?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  state?: string | null;
  state_code?: string | null;
  pincode?: string | null;
}

export const vendorService = {
  list: (companyId: string, page = 1, pageSize = 50, search?: string) =>
    apiClient.get<PaginatedData<Vendor>>(
      `/accounting/vendors?${qs({ company_id: companyId, page, page_size: pageSize, search })}`
    ),
  create: (companyId: string, payload: VendorPayload) =>
    apiClient.post<Vendor>(`/accounting/vendors?company_id=${companyId}`, payload),
  update: (companyId: string, id: string, payload: Partial<VendorPayload & { is_active: boolean }>) =>
    apiClient.patch<Vendor>(`/accounting/vendors/${id}?company_id=${companyId}`, payload),
};

export interface ProductPayload {
  name: string;
  code?: string | null;
  item_type: string;
  description?: string | null;
  hsn_sac?: string | null;
  unit?: string | null;
  tax_rate?: string;
}

export const productService = {
  list: (companyId: string, page = 1, pageSize = 50, search?: string) =>
    apiClient.get<PaginatedData<ProductServiceItem>>(
      `/accounting/products?${qs({ company_id: companyId, page, page_size: pageSize, search })}`
    ),
  create: (companyId: string, payload: ProductPayload) =>
    apiClient.post<ProductServiceItem>(`/accounting/products?company_id=${companyId}`, payload),
  update: (companyId: string, id: string, payload: Partial<ProductPayload & { is_active: boolean }>) =>
    apiClient.patch<ProductServiceItem>(`/accounting/products/${id}?company_id=${companyId}`, payload),
};
