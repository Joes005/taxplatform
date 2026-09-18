import { apiClient } from "@/lib/api-client";
import type { AuditReview, AuditReviewType } from "@/types/audit";

export const auditReviewService = {
  list: (companyId: string, engagementId: string) =>
    apiClient.get<AuditReview[]>(`/audits/engagements/${engagementId}/reviews?company_id=${companyId}`),
  start: (companyId: string, engagementId: string, reviewType: AuditReviewType) =>
    apiClient.post<AuditReview>(`/audits/engagements/${engagementId}/reviews?company_id=${companyId}`, {
      review_type: reviewType,
    }),
  complete: (companyId: string, engagementId: string, reviewId: string, summary?: string, notes?: string) =>
    apiClient.post<AuditReview>(
      `/audits/engagements/${engagementId}/reviews/${reviewId}/complete?company_id=${companyId}`,
      { summary, notes }
    ),
  return: (companyId: string, engagementId: string, reviewId: string, notes: string) =>
    apiClient.post<AuditReview>(
      `/audits/engagements/${engagementId}/reviews/${reviewId}/return?company_id=${companyId}`,
      { notes }
    ),
};
