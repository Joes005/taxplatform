import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { auditReviewService } from "@/services/auditReviewService";
import type { AuditReviewType } from "@/types/audit";

const keys = {
  list: (companyId: string, engagementId: string) => ["audit-reviews", companyId, engagementId] as const,
};

export function useAuditReviews(companyId: string | undefined, engagementId: string | undefined) {
  return useQuery({
    queryKey: companyId && engagementId ? keys.list(companyId, engagementId) : ["audit-reviews", "none"],
    queryFn: () => auditReviewService.list(companyId as string, engagementId as string),
    enabled: !!companyId && !!engagementId,
  });
}

export function useStartAuditReview(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reviewType: AuditReviewType) => auditReviewService.start(companyId, engagementId, reviewType),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list(companyId, engagementId) }),
  });
}

export function useCompleteAuditReview(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, summary, notes }: { reviewId: string; summary?: string; notes?: string }) =>
      auditReviewService.complete(companyId, engagementId, reviewId, summary, notes),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list(companyId, engagementId) }),
  });
}

export function useReturnAuditReview(companyId: string, engagementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, notes }: { reviewId: string; notes: string }) =>
      auditReviewService.return(companyId, engagementId, reviewId, notes),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list(companyId, engagementId) }),
  });
}
