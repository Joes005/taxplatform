import { apiClient } from "@/lib/api-client";
import type { CompanyUser, MembershipStatus, PaginatedData } from "@/types/api";

export interface CreateCompanyUserPayload {
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  role_code: string;
}

export interface UpdateCompanyUserPayload {
  first_name?: string;
  last_name?: string;
  role_code?: string;
  status?: MembershipStatus;
}

export const userService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<CompanyUser>>(
      `/companies/${companyId}/users?page=${page}&page_size=${pageSize}`
    ),

  create: (companyId: string, payload: CreateCompanyUserPayload) =>
    apiClient.post<CompanyUser>(`/companies/${companyId}/users`, payload),

  update: (companyId: string, userId: string, payload: UpdateCompanyUserPayload) =>
    apiClient.patch<CompanyUser>(`/companies/${companyId}/users/${userId}`, payload),

  deactivate: (companyId: string, userId: string) =>
    apiClient.delete<CompanyUser>(`/companies/${companyId}/users/${userId}`),
};
