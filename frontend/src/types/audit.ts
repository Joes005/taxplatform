// Phase 7 — CA/Auditor Workflow types. Named `audit.ts`/"AuditEngagement"
// etc. — kept unambiguous next to the pre-existing platform AuditLog
// (types/api.ts) which this phase never touches.

export type AuditEngagementType =
  | "INTERNAL_REVIEW"
  | "TAX_COMPLIANCE_REVIEW"
  | "FINANCIAL_REVIEW"
  | "BOOKS_REVIEW"
  | "PRE_AUDIT_REVIEW"
  | "GENERAL_AUDIT"
  | "OTHER";

export type AuditEngagementStatus =
  | "DRAFT"
  | "OPEN"
  | "ASSIGNED"
  | "IN_REVIEW"
  | "PENDING_CLIENT_ACTION"
  | "PENDING_AUDITOR_REVIEW"
  | "APPROVED"
  | "SIGNED_OFF"
  | "CLOSED"
  | "CANCELLED";

export type AuditAssignmentRole = "LEAD_AUDITOR" | "AUDITOR" | "REVIEWER" | "ACCOUNTANT" | "CLIENT_CONTACT";

export type AuditChecklistItemStatus = "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED" | "NOT_APPLICABLE" | "REQUIRES_ATTENTION";
export type AuditChecklistCategory = "ACCOUNTING" | "GST" | "TDS" | "BANK" | "DOCUMENTS" | "INTERNAL_CONTROLS" | "OTHER";

export type AuditFindingCategory =
  | "ACCOUNTING" | "GST" | "TDS" | "BANK" | "DOCUMENT" | "DATA_QUALITY" | "CONTROL" | "COMPLIANCE" | "PROCESS" | "OTHER";
export type AuditFindingSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type AuditFindingStatus =
  | "OPEN" | "ASSIGNED" | "IN_REVIEW" | "ACTION_REQUIRED" | "RESPONSE_SUBMITTED"
  | "RESOLVED" | "REOPENED" | "CLOSED" | "REJECTED";
export type AuditFindingSourceType =
  | "DOCUMENT" | "SALES_INVOICE" | "PURCHASE_INVOICE" | "PAYMENT" | "RECEIPT" | "JOURNAL_ENTRY"
  | "GST_RETURN_PERIOD" | "GSTR2B_RECORD" | "TDS_TRANSACTION" | "TDS_CHALLAN"
  | "BANK_TRANSACTION" | "BANK_RECONCILIATION" | "OTHER";
export type AuditFindingResponseStatus = "DRAFT" | "SUBMITTED" | "ACCEPTED" | "REJECTED";

export type AuditReviewType = "INITIAL_REVIEW" | "FINAL_REVIEW" | "SECOND_REVIEW" | "QUALITY_REVIEW";
export type AuditReviewStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "RETURNED";
export type AuditSignOffType = "LEAD_AUDITOR" | "REVIEWER" | "COMPANY_ACKNOWLEDGEMENT";

export interface AuditEngagement {
  id: string;
  company_id: string;
  engagement_code: string;
  title: string;
  description: string | null;
  financial_year_id: string;
  period_start: string;
  period_end: string;
  engagement_type: AuditEngagementType;
  status: AuditEngagementStatus;
  is_locked: boolean;
  locked_at: string | null;
  locked_by: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AuditAssignment {
  id: string;
  engagement_id: string;
  company_id: string;
  user_id: string;
  role: AuditAssignmentRole;
  assigned_by: string;
  assigned_at: string;
  unassigned_at: string | null;
  is_active: boolean;
}

export interface AuditChecklistItem {
  id: string;
  checklist_id: string;
  engagement_id: string;
  company_id: string;
  category: AuditChecklistCategory;
  title: string;
  description: string | null;
  order_index: number;
  status: AuditChecklistItemStatus;
  assigned_to: string | null;
  completed_by: string | null;
  completed_at: string | null;
  notes: string | null;
}

export interface AuditChecklist {
  id: string;
  engagement_id: string;
  company_id: string;
  name: string;
  items: AuditChecklistItem[];
}

export interface AuditFinding {
  id: string;
  engagement_id: string;
  company_id: string;
  finding_code: string;
  title: string;
  description: string | null;
  category: AuditFindingCategory;
  severity: AuditFindingSeverity;
  status: AuditFindingStatus;
  source_type: AuditFindingSourceType | null;
  source_id: string | null;
  assigned_to: string | null;
  created_by: string;
  due_date: string | null;
  resolution_summary: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditFindingCreateResult {
  finding: AuditFinding;
  duplicate_warning: boolean;
  duplicate_finding_codes: string[];
}

export interface AuditFindingComment {
  id: string;
  finding_id: string;
  user_id: string;
  comment: string;
  created_at: string;
}

export interface AuditFindingEvidence {
  id: string;
  finding_id: string;
  document_id: string;
  description: string | null;
  added_by: string;
  added_at: string;
}

export interface AuditFindingResponse {
  id: string;
  finding_id: string;
  submitted_by: string;
  response_text: string;
  submitted_at: string;
  status: AuditFindingResponseStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_comment: string | null;
}

export interface AuditReview {
  id: string;
  engagement_id: string;
  company_id: string;
  reviewer_id: string;
  review_type: AuditReviewType;
  status: AuditReviewStatus;
  summary: string | null;
  notes: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface AuditSignOff {
  id: string;
  engagement_id: string;
  company_id: string;
  signed_by: string;
  sign_off_type: AuditSignOffType;
  statement: string;
  created_at: string;
}

export interface AuditEngagementProgress {
  engagement: AuditEngagement;
  checklist_total: number;
  checklist_completed: number;
  findings_total: number;
  findings_open: number;
  findings_by_severity: Record<AuditFindingSeverity, number>;
}

export interface AuditReviewQueueItem {
  engagement: AuditEngagement;
  open_findings: number;
  high_or_critical_open_findings: number;
  pending_responses: number;
}

export interface AuditWorkflowDashboard {
  engagements_by_status: Record<AuditEngagementStatus, number>;
  findings_by_status: Record<AuditFindingStatus, number>;
  review_queue: AuditReviewQueueItem[];
}
