import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { notificationService } from "@/services/notificationService";

const keys = {
  all: (companyId: string) => ["notifications", companyId] as const,
  list: (companyId: string, page: number) => ["notifications", companyId, "list", page] as const,
  unread: (companyId: string) => ["notifications", companyId, "unread"] as const,
  unreadCount: (companyId: string) => ["notifications", companyId, "unread-count"] as const,
};

export function useNotifications(companyId: string | undefined, page = 1) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page) : ["notifications", "none"],
    queryFn: () => notificationService.list(companyId as string, page),
    enabled: !!companyId,
  });
}

export function useUnreadNotifications(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? keys.unread(companyId) : ["notifications", "none"],
    queryFn: () => notificationService.listUnread(companyId as string, 1, 10),
    enabled: !!companyId,
  });
}

export function useUnreadNotificationCount(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? keys.unreadCount(companyId) : ["notifications", "none"],
    queryFn: () => notificationService.unreadCount(companyId as string),
    enabled: !!companyId,
    refetchInterval: 60_000,
  });
}

export function useMarkNotificationRead(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationService.markRead(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useMarkAllNotificationsRead(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationService.markAllRead(companyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
