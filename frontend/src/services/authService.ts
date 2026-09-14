import { apiClient } from "@/lib/api-client";
import type { ActiveCompanyContext, LoginResponseData, User } from "@/types/api";

export const authService = {
  login: (email: string, password: string) =>
    apiClient.post<LoginResponseData>("/auth/login", { email, password }, { skipAuth: true }),

  register: (payload: {
    first_name: string;
    last_name: string;
    email: string;
    password: string;
  }) => apiClient.post<User>("/auth/register", payload, { skipAuth: true }),

  logout: (refreshToken: string) => apiClient.post<null>("/auth/logout", { refresh_token: refreshToken }),

  selectCompany: (companyId: string) =>
    apiClient.post<ActiveCompanyContext>("/auth/select-company", { company_id: companyId }),

  me: () => apiClient.get<User>("/auth/me"),
};
