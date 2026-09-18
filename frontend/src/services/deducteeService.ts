import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { Deductee, DeducteeType } from "@/types/tds";

export interface DeducteePayload {
  name: string;
  code?: string | null;
  vendor_id?: string | null;
  customer_id?: string | null;
  pan?: string | null;
  deductee_type?: DeducteeType;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  state?: string | null;
  state_code?: string | null;
  pincode?: string | null;
  is_active?: boolean;
}

export const deducteeService = {
  list: (companyId: string, page = 1, pageSize = 20, search?: string) =>
    apiClient.get<PaginatedData<Deductee>>(
      `/tds/deductees?company_id=${companyId}&page=${page}&page_size=${pageSize}` +
        (search ? `&search=${encodeURIComponent(search)}` : "")
    ),
  get: (companyId: string, deducteeId: string) =>
    apiClient.get<Deductee>(`/tds/deductees/${deducteeId}?company_id=${companyId}`),
  create: (companyId: string, payload: DeducteePayload) =>
    apiClient.post<Deductee>(`/tds/deductees?company_id=${companyId}`, payload),
  update: (companyId: string, deducteeId: string, payload: Partial<DeducteePayload>) =>
    apiClient.patch<Deductee>(`/tds/deductees/${deducteeId}?company_id=${companyId}`, payload),
};
