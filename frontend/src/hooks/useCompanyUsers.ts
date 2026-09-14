import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  userService,
  type CreateCompanyUserPayload,
  type UpdateCompanyUserPayload,
} from "@/services/userService";

export function useCompanyUsers(companyId: string | undefined, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["company-users", companyId, page, pageSize],
    queryFn: () => userService.list(companyId as string, page, pageSize),
    enabled: !!companyId,
  });
}

export function useCreateCompanyUser(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCompanyUserPayload) => userService.create(companyId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["company-users", companyId] }),
  });
}

export function useUpdateCompanyUser(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, payload }: { userId: string; payload: UpdateCompanyUserPayload }) =>
      userService.update(companyId, userId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["company-users", companyId] }),
  });
}

export function useDeactivateCompanyUser(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => userService.deactivate(companyId, userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["company-users", companyId] }),
  });
}
