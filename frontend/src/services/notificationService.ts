import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { Notification } from "@/types/compliance";

export const notificationService = {
  list: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<Notification>>(`/notifications?company_id=${companyId}&page=${page}&page_size=${pageSize}`),
  listUnread: (companyId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<Notification>>(
      `/notifications/unread?company_id=${companyId}&page=${page}&page_size=${pageSize}`
    ),
  unreadCount: (companyId: string) =>
    apiClient.get<{ unread_count: number }>(`/notifications/unread-count?company_id=${companyId}`),
  markRead: (companyId: string, id: string) =>
    apiClient.patch<Notification>(`/notifications/${id}/read?company_id=${companyId}`),
  markAllRead: (companyId: string) => apiClient.post<null>(`/notifications/read-all?company_id=${companyId}`),
};
