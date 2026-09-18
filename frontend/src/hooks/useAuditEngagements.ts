import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  auditEngagementService,
  type AuditEngagementCreatePayload,
  type AuditEngagementUpdatePayload,
} from "@/services/auditEngagementService";
import type { AuditAssignmentRole, AuditSignOffType } from "@/types/audit";

const keys = {
  all: (companyId: string) => ["audit-engagements", companyId] as const,
  list: (companyId: string, page: number, status?: string) => ["audit-engagements", companyId, "list", page, status] as const,
  detail: (companyId: string, id: string) => ["audit-engagements", companyId, "detail", id] as const,
  assignments: (companyId: string, id: string) => ["audit-engagements", companyId, "assignments", id] as const,
  signoffs: (companyId: string, id: string) => ["audit-engagements", companyId, "signoffs", id] as const,
};

export function useAuditEngagements(companyId: string | undefined, page = 1, status?: string) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, page, status) : ["audit-engagements", "none"],
    queryFn: () => auditEngagementService.list(companyId as string, page, 20, status),
    enabled: !!companyId,
  });
}

export function useAuditEngagement(companyId: string | undefined, engagementId: string | undefined) {
  return useQuery({
    queryKey: companyId && engagementId ? keys.detail(companyId, engagementId) : ["audit-engagements", "none"],
    queryFn: () => auditEngagementService.get(companyId as string, engagementId as string),
    enabled: !!companyId && !!engagementId,
  });
}

export function useCreateAuditEngagement(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AuditEngagementCreatePayload) => auditEngagementService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useUpdateAuditEngagement(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AuditEngagementUpdatePayload) => auditEngagementService.update(companyId, engagementId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) }),
  });
}

function useEngagementAction(companyId: string, engagementId: string, fn: (companyId: string, engagementId: string) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => fn(companyId, engagementId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) });
      qc.invalidateQueries({ queryKey: keys.all(companyId) });
    },
  });
}

export function useOpenAuditEngagement(companyId: string, engagementId: string) {
  return useEngagementAction(companyId, engagementId, auditEngagementService.open);
}
export function useStartAuditEngagementReview(companyId: string, engagementId: string) {
  return useEngagementAction(companyId, engagementId, auditEngagementService.startReview);
}
export function useResumeAuditEngagementReview(companyId: string, engagementId: string) {
  return useEngagementAction(companyId, engagementId, auditEngagementService.resumeReview);
}
export function useSubmitAuditEngagementForReview(companyId: string, engagementId: string) {
  return useEngagementAction(companyId, engagementId, auditEngagementService.submitForReview);
}
export function useMarkAuditEngagementSignedOff(companyId: string, engagementId: string) {
  return useEngagementAction(companyId, engagementId, auditEngagementService.markSignedOff);
}
export function useCloseAuditEngagement(companyId: string, engagementId: string) {
  return useEngagementAction(companyId, engagementId, auditEngagementService.close);
}
export function useLockAuditEngagement(companyId: string, engagementId: string) {
  return useEngagementAction(companyId, engagementId, auditEngagementService.lock);
}

export function useRequestAuditClientAction(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (comment?: string) => auditEngagementService.requestClientAction(companyId, engagementId, comment),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) }),
  });
}
export function useApproveAuditEngagement(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (comment?: string) => auditEngagementService.approve(companyId, engagementId, comment),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) }),
  });
}
export function useReturnAuditEngagementForChanges(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (comment?: string) => auditEngagementService.returnForChanges(companyId, engagementId, comment),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) }),
  });
}
export function useCancelAuditEngagement(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (comment?: string) => auditEngagementService.cancel(companyId, engagementId, comment),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) }),
  });
}

export function useAuditSignOffs(companyId: string | undefined, engagementId: string | undefined) {
  return useQuery({
    queryKey: companyId && engagementId ? keys.signoffs(companyId, engagementId) : ["audit-signoffs", "none"],
    queryFn: () => auditEngagementService.listSignOffs(companyId as string, engagementId as string),
    enabled: !!companyId && !!engagementId,
  });
}
export function useCreateAuditSignOff(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (signOffType: AuditSignOffType) => auditEngagementService.createSignOff(companyId, engagementId, signOffType),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.signoffs(companyId, engagementId) });
      qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) });
    },
  });
}

export function useAuditAssignments(companyId: string | undefined, engagementId: string | undefined) {
  return useQuery({
    queryKey: companyId && engagementId ? keys.assignments(companyId, engagementId) : ["audit-assignments", "none"],
    queryFn: () => auditEngagementService.listAssignments(companyId as string, engagementId as string),
    enabled: !!companyId && !!engagementId,
  });
}
export function useAssignAuditEngagementUser(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: AuditAssignmentRole }) =>
      auditEngagementService.assign(companyId, engagementId, userId, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.assignments(companyId, engagementId) });
      qc.invalidateQueries({ queryKey: keys.detail(companyId, engagementId) });
    },
  });
}
export function useUnassignAuditEngagementUser(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (assignmentId: string) => auditEngagementService.unassign(companyId, engagementId, assignmentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.assignments(companyId, engagementId) }),
  });
}
