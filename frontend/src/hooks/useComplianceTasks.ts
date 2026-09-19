import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  complianceTaskService,
  type ComplianceTaskCreatePayload,
  type ComplianceTaskListFilters,
} from "@/services/complianceTaskService";

const keys = {
  all: (companyId: string) => ["compliance-tasks", companyId] as const,
  list: (companyId: string, filters: ComplianceTaskListFilters) => ["compliance-tasks", companyId, "list", filters] as const,
  detail: (companyId: string, id: string) => ["compliance-tasks", companyId, "detail", id] as const,
  comments: (companyId: string, id: string) => ["compliance-tasks", companyId, "comments", id] as const,
  evidence: (companyId: string, id: string) => ["compliance-tasks", companyId, "evidence", id] as const,
};

export function useComplianceTasks(companyId: string | undefined, filters: ComplianceTaskListFilters = {}) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId, filters) : ["compliance-tasks", "none"],
    queryFn: () => complianceTaskService.list(companyId as string, filters),
    enabled: !!companyId,
  });
}

export function useComplianceTask(companyId: string | undefined, id: string | undefined) {
  return useQuery({
    queryKey: companyId && id ? keys.detail(companyId, id) : ["compliance-tasks", "none"],
    queryFn: () => complianceTaskService.get(companyId as string, id as string),
    enabled: !!companyId && !!id,
  });
}

export function useCreateComplianceTask(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ComplianceTaskCreatePayload) => complianceTaskService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useUpdateComplianceTask(companyId: string, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<ComplianceTaskCreatePayload>) => complianceTaskService.update(companyId, id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, id) }),
  });
}

export function useAssignComplianceTask(companyId: string, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ assignedTo, reviewerId }: { assignedTo?: string; reviewerId?: string }) =>
      complianceTaskService.assign(companyId, id, assignedTo, reviewerId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, id) });
      qc.invalidateQueries({ queryKey: keys.all(companyId) });
    },
  });
}

function useTaskAction(companyId: string, id: string, fn: (companyId: string, id: string) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => fn(companyId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, id) });
      qc.invalidateQueries({ queryKey: keys.all(companyId) });
    },
  });
}

export function useStartComplianceTask(companyId: string, id: string) {
  return useTaskAction(companyId, id, complianceTaskService.start);
}
export function useSubmitComplianceTaskForReview(companyId: string, id: string) {
  return useTaskAction(companyId, id, complianceTaskService.submitReview);
}
export function useVerifyComplianceTask(companyId: string, id: string) {
  return useTaskAction(companyId, id, complianceTaskService.verify);
}
export function useLockComplianceTask(companyId: string, id: string) {
  return useTaskAction(companyId, id, complianceTaskService.lock);
}

export function useCompleteComplianceTask(companyId: string, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (notes?: string) => complianceTaskService.complete(companyId, id, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, id) });
      qc.invalidateQueries({ queryKey: keys.all(companyId) });
    },
  });
}

export function useReturnComplianceTaskForChanges(companyId: string, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => complianceTaskService.returnForChanges(companyId, id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, id) });
      qc.invalidateQueries({ queryKey: keys.all(companyId) });
    },
  });
}

export function useCancelComplianceTask(companyId: string, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason?: string) => complianceTaskService.cancel(companyId, id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, id) });
      qc.invalidateQueries({ queryKey: keys.all(companyId) });
    },
  });
}

export function useComplianceTaskComments(companyId: string | undefined, id: string | undefined) {
  return useQuery({
    queryKey: companyId && id ? keys.comments(companyId, id) : ["compliance-task-comments", "none"],
    queryFn: () => complianceTaskService.listComments(companyId as string, id as string),
    enabled: !!companyId && !!id,
  });
}
export function useAddComplianceTaskComment(companyId: string, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (comment: string) => complianceTaskService.addComment(companyId, id, comment),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.comments(companyId, id) }),
  });
}

export function useComplianceTaskEvidence(companyId: string | undefined, id: string | undefined) {
  return useQuery({
    queryKey: companyId && id ? keys.evidence(companyId, id) : ["compliance-task-evidence", "none"],
    queryFn: () => complianceTaskService.listEvidence(companyId as string, id as string),
    enabled: !!companyId && !!id,
  });
}
export function useAddComplianceTaskEvidence(companyId: string, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, description }: { documentId: string; description?: string }) =>
      complianceTaskService.addEvidence(companyId, id, documentId, description),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.evidence(companyId, id) }),
  });
}
export function useRemoveComplianceTaskEvidence(companyId: string, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (evidenceId: string) => complianceTaskService.removeEvidence(companyId, id, evidenceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.evidence(companyId, id) }),
  });
}
