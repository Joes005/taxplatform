import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { auditFindingService, type AuditFindingCreatePayload, type AuditFindingUpdatePayload } from "@/services/auditFindingService";
import type { AuditFindingStatus } from "@/types/audit";

const keys = {
  engagementList: (companyId: string, engagementId: string, page: number) =>
    ["audit-findings", companyId, "engagement", engagementId, page] as const,
  companyList: (companyId: string, page: number) => ["audit-findings", companyId, "company", page] as const,
  detail: (companyId: string, id: string) => ["audit-findings", companyId, "detail", id] as const,
  comments: (companyId: string, id: string) => ["audit-findings", companyId, "comments", id] as const,
  evidence: (companyId: string, id: string) => ["audit-findings", companyId, "evidence", id] as const,
  responses: (companyId: string, id: string) => ["audit-findings", companyId, "responses", id] as const,
};

export function useAuditFindingsForEngagement(
  companyId: string | undefined,
  engagementId: string | undefined,
  page = 1,
  status?: AuditFindingStatus
) {
  return useQuery({
    queryKey: companyId && engagementId ? keys.engagementList(companyId, engagementId, page) : ["audit-findings", "none"],
    queryFn: () => auditFindingService.listForEngagement(companyId as string, engagementId as string, page, 20, status),
    enabled: !!companyId && !!engagementId,
  });
}

export function useAuditFindingsForCompany(companyId: string | undefined, page = 1, status?: AuditFindingStatus) {
  return useQuery({
    queryKey: companyId ? keys.companyList(companyId, page) : ["audit-findings", "none"],
    queryFn: () => auditFindingService.listForCompany(companyId as string, page, 20, status),
    enabled: !!companyId,
  });
}

export function useAuditFinding(companyId: string | undefined, findingId: string | undefined) {
  return useQuery({
    queryKey: companyId && findingId ? keys.detail(companyId, findingId) : ["audit-findings", "none"],
    queryFn: () => auditFindingService.get(companyId as string, findingId as string),
    enabled: !!companyId && !!findingId,
  });
}

export function useCreateAuditFinding(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AuditFindingCreatePayload) => auditFindingService.create(companyId, engagementId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["audit-findings", companyId] }),
  });
}

export function useUpdateAuditFinding(companyId: string, findingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AuditFindingUpdatePayload) => auditFindingService.update(companyId, findingId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(companyId, findingId) }),
  });
}

function useFindingVoidAction(
  companyId: string,
  findingId: string,
  fn: (companyId: string, findingId: string) => Promise<unknown>
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => fn(companyId, findingId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, findingId) });
      qc.invalidateQueries({ queryKey: ["audit-findings", companyId] });
    },
  });
}

function useFindingTextAction(
  companyId: string,
  findingId: string,
  fn: (companyId: string, findingId: string, text: string) => Promise<unknown>
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => fn(companyId, findingId, text),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(companyId, findingId) });
      qc.invalidateQueries({ queryKey: ["audit-findings", companyId] });
    },
  });
}

export function useAssignAuditFinding(companyId: string, findingId: string) {
  return useFindingTextAction(companyId, findingId, auditFindingService.assign);
}
export function useStartAuditFindingReview(companyId: string, findingId: string) {
  return useFindingVoidAction(companyId, findingId, auditFindingService.startReview);
}
export function useRequestAuditFindingAction(companyId: string, findingId: string) {
  return useFindingVoidAction(companyId, findingId, auditFindingService.requestAction);
}
export function useResolveAuditFinding(companyId: string, findingId: string) {
  return useFindingTextAction(companyId, findingId, auditFindingService.resolve);
}
export function useCloseAuditFinding(companyId: string, findingId: string) {
  return useFindingVoidAction(companyId, findingId, auditFindingService.close);
}
export function useReopenAuditFinding(companyId: string, findingId: string) {
  return useFindingTextAction(companyId, findingId, auditFindingService.reopen);
}
export function useRejectAuditFinding(companyId: string, findingId: string) {
  return useFindingTextAction(companyId, findingId, auditFindingService.reject);
}

export function useAuditFindingComments(companyId: string | undefined, findingId: string | undefined) {
  return useQuery({
    queryKey: companyId && findingId ? keys.comments(companyId, findingId) : ["audit-finding-comments", "none"],
    queryFn: () => auditFindingService.listComments(companyId as string, findingId as string),
    enabled: !!companyId && !!findingId,
  });
}
export function useAddAuditFindingComment(companyId: string, findingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (comment: string) => auditFindingService.addComment(companyId, findingId, comment),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.comments(companyId, findingId) }),
  });
}

export function useAuditFindingEvidence(companyId: string | undefined, findingId: string | undefined) {
  return useQuery({
    queryKey: companyId && findingId ? keys.evidence(companyId, findingId) : ["audit-finding-evidence", "none"],
    queryFn: () => auditFindingService.listEvidence(companyId as string, findingId as string),
    enabled: !!companyId && !!findingId,
  });
}
export function useAddAuditFindingEvidence(companyId: string, findingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, description }: { documentId: string; description?: string }) =>
      auditFindingService.addEvidence(companyId, findingId, documentId, description),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.evidence(companyId, findingId) }),
  });
}
export function useRemoveAuditFindingEvidence(companyId: string, findingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (evidenceId: string) => auditFindingService.removeEvidence(companyId, findingId, evidenceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.evidence(companyId, findingId) }),
  });
}

export function useAuditFindingResponses(companyId: string | undefined, findingId: string | undefined) {
  return useQuery({
    queryKey: companyId && findingId ? keys.responses(companyId, findingId) : ["audit-finding-responses", "none"],
    queryFn: () => auditFindingService.listResponses(companyId as string, findingId as string),
    enabled: !!companyId && !!findingId,
  });
}
export function useSubmitAuditFindingResponse(companyId: string, findingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (responseText: string) => auditFindingService.submitResponse(companyId, findingId, responseText),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.responses(companyId, findingId) });
      qc.invalidateQueries({ queryKey: keys.detail(companyId, findingId) });
    },
  });
}
export function useReviewAuditFindingResponse(companyId: string, findingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ responseId, accept, reviewComment }: { responseId: string; accept: boolean; reviewComment?: string }) =>
      auditFindingService.reviewResponse(companyId, findingId, responseId, accept, reviewComment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.responses(companyId, findingId) });
      qc.invalidateQueries({ queryKey: keys.detail(companyId, findingId) });
    },
  });
}
