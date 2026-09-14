import { apiClient } from "@/lib/api-client";
import type { Role } from "@/types/api";

export const roleService = {
  list: () => apiClient.get<Role[]>("/roles"),
};
