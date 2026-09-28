import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  complianceObligationService,
  type ComplianceObligationCreatePayload,
  type ObligationListFilters,
} from "@/services/complianceObligationService";

export function useComplianceControlCenter(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? ["compliance-control-center", companyId] : ["compliance-control-center", "none"],
    queryFn: () => complianceObligationService.getControlCenter(companyId as string),
    enabled: !!companyId,
    refetchInterval: 30000,
  });
}

export function useComplianceHealth(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? ["compliance-health", companyId] : ["compliance-health", "none"],
    queryFn: () => complianceObligationService.getHealth(companyId as string),
    enabled: !!companyId,
  });
}

export function useComplianceObligations(companyId: string | undefined, filters: ObligationListFilters = {}) {
  return useQuery({
    queryKey: companyId ? ["compliance-obligations", companyId, filters] : ["compliance-obligations", "none"],
    queryFn: () => complianceObligationService.list(companyId as string, filters),
    enabled: !!companyId,
  });
}

export function useComplianceObligation(companyId: string | undefined, obligationId: string | undefined) {
  return useQuery({
    queryKey: companyId && obligationId ? ["compliance-obligation", companyId, obligationId] : ["compliance-obligation", "none"],
    queryFn: () => complianceObligationService.get(companyId as string, obligationId as string),
    enabled: !!companyId && !!obligationId,
  });
}

export function useCreateComplianceObligation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ComplianceObligationCreatePayload) => complianceObligationService.create(companyId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-health", companyId] });
    },
  });
}

export function useUpdateComplianceObligation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obligationId, payload }: { obligationId: string; payload: Partial<ComplianceObligationCreatePayload> }) =>
      complianceObligationService.update(companyId, obligationId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
    },
  });
}

export function useAssignComplianceObligation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      obligationId,
      assignedTo,
      reviewerId,
    }: {
      obligationId: string;
      assignedTo?: string | null;
      reviewerId?: string | null;
    }) => complianceObligationService.assign(companyId, obligationId, assignedTo, reviewerId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
    },
  });
}

export function useRunObligationReadiness(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (obligationId: string) => complianceObligationService.runReadiness(companyId, obligationId),
    onSuccess: (_data, obligationId) => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-obligation", companyId, obligationId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-health", companyId] });
    },
  });
}

export function useSubmitObligationReview(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obligationId, reviewNotes }: { obligationId: string; reviewNotes?: string }) =>
      complianceObligationService.submitReview(companyId, obligationId, reviewNotes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
    },
  });
}

export function useApproveObligation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obligationId, reviewNotes }: { obligationId: string; reviewNotes?: string }) =>
      complianceObligationService.approve(companyId, obligationId, reviewNotes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-health", companyId] });
    },
  });
}

export function useRejectObligation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obligationId, reviewNotes }: { obligationId: string; reviewNotes?: string }) =>
      complianceObligationService.reject(companyId, obligationId, reviewNotes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
    },
  });
}

export function useCompleteObligation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obligationId, completionNotes }: { obligationId: string; completionNotes?: string }) =>
      complianceObligationService.complete(companyId, obligationId, completionNotes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-health", companyId] });
    },
  });
}

export function useReopenObligation(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obligationId, reason }: { obligationId: string; reason: string }) =>
      complianceObligationService.reopen(companyId, obligationId, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-health", companyId] });
    },
  });
}

export function useObligationEvidence(companyId: string | undefined, obligationId: string | undefined) {
  return useQuery({
    queryKey: companyId && obligationId ? ["compliance-obligation-evidence", companyId, obligationId] : ["compliance-obligation-evidence", "none"],
    queryFn: () => complianceObligationService.listEvidence(companyId as string, obligationId as string),
    enabled: !!companyId && !!obligationId,
  });
}

export function useAttachObligationEvidence(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      obligationId,
      documentId,
      description,
    }: {
      obligationId: string;
      documentId: string;
      description?: string;
    }) => complianceObligationService.attachEvidence(companyId, obligationId, documentId, description),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["compliance-obligation-evidence", companyId, variables.obligationId] });
    },
  });
}

export function useRemoveObligationEvidence(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obligationId, evidenceId }: { obligationId: string; evidenceId: string }) =>
      complianceObligationService.removeEvidence(companyId, obligationId, evidenceId),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["compliance-obligation-evidence", companyId, variables.obligationId] });
    },
  });
}

export function useGenerateComplianceTask(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obligationId, title }: { obligationId: string; title?: string }) =>
      complianceObligationService.generateTask(companyId, obligationId, title),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance-tasks", companyId] }),
  });
}

export function useSweepOverdueObligations(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => complianceObligationService.sweepOverdue(companyId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-obligations", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-control-center", companyId] });
      qc.invalidateQueries({ queryKey: ["compliance-health", companyId] });
    },
  });
}
