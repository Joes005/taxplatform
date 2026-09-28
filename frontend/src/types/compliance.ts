// Phase 9 & Phase 13 — Compliance Control Center, Obligations, Readiness & Tasks.

export type ComplianceCategory = "GST" | "TDS" | "INCOME_TAX" | "AUDIT" | "ACCOUNTING" | "BANK" | "GENERAL" | "OTHER";
export type ComplianceModule = "GST" | "TDS" | "INCOME_TAX" | "AUDIT" | "BANK_RECONCILIATION" | "ACCOUNTING" | "DOCUMENTS" | "GENERAL";
export type ComplianceFrequency = "MONTHLY" | "QUARTERLY" | "ANNUAL" | "ONE_TIME" | "CUSTOM";
export type CompliancePriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ComplianceObligationStatus =
  | "DRAFT"
  | "ACTIVE"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "READY_FOR_REVIEW"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "COMPLETED"
  | "FULFILLED"
  | "REJECTED"
  | "BLOCKED"
  | "OVERDUE"
  | "CANCELLED"
  | "REOPENED";

export type ReadinessStatus = "READY" | "READY_WITH_WARNINGS" | "BLOCKED" | "MISSING_DATA" | "NOT_APPLICABLE";
export type ComplianceHealthStatus = "HEALTHY" | "ATTENTION_REQUIRED" | "AT_RISK" | "OVERDUE";

export type ComplianceTaskStatus =
  | "PENDING" | "IN_PROGRESS" | "PENDING_REVIEW" | "COMPLETED" | "VERIFIED" | "OVERDUE" | "CANCELLED" | "LOCKED";
export type ComplianceSourceType =
  | "GST_RETURN" | "TDS_RETURN" | "INCOME_TAX_RETURN" | "AUDIT_ENGAGEMENT" | "AUDIT_CHECKLIST"
  | "BANK_RECONCILIATION" | "ACCOUNTING_PERIOD" | "DOCUMENT" | "MANUAL";
export type NotificationType =
  | "TASK_ASSIGNED" | "TASK_DUE_SOON" | "TASK_OVERDUE" | "TASK_REVIEW_REQUIRED"
  | "TASK_COMPLETED" | "TASK_VERIFIED" | "COMMENT_ADDED" | "TASK_REASSIGNED"
  | "OBLIGATION_ASSIGNED" | "OBLIGATION_DUE_SOON" | "OBLIGATION_OVERDUE" | "OBLIGATION_REVIEW"
  | "OBLIGATION_APPROVED" | "OBLIGATION_REJECTED" | "OBLIGATION_COMPLETED" | "OBLIGATION_BLOCKED"
  | "OBLIGATION_REOPENED";

export type NotificationSeverity = "INFO" | "WARNING" | "CRITICAL";

export interface ComplianceRule {
  id: string;
  company_id: string | null;
  code: string;
  name: string;
  description: string | null;
  category: ComplianceCategory;
  module: ComplianceModule;
  frequency: ComplianceFrequency;
  due_date_rule: Record<string, unknown>;
  priority: CompliancePriority;
  effective_from: string;
  effective_to: string | null;
  version: number;
  is_active: boolean;
}

export interface ReadinessCheckItem {
  check_code: string;
  description: string;
  status: "PASS" | "WARN" | "FAIL" | "INFO";
  blocking: boolean;
  source_module: string;
  entity_reference: string | null;
  remediation_action: string;
  deep_link: string;
}

export interface ReadinessResult {
  obligation_id: string;
  overall_status: ReadinessStatus;
  checks: ReadinessCheckItem[];
  checked_at: string;
  blocking_issues_count: number;
  blocking_failures?: string[];
  warnings?: string[];
}

export type ReadinessCheckDetail = ReadinessCheckItem;

export interface ComplianceObligation {
  id: string;
  company_id: string;
  code: string;
  name: string;
  description: string | null;
  category: ComplianceCategory;
  module: ComplianceModule;
  frequency: ComplianceFrequency;
  financial_year_id: string | null;
  tax_period: string | null;
  start_date: string;
  due_date: string;
  grace_date: string | null;
  priority: CompliancePriority;
  status: ComplianceObligationStatus;
  is_recurring: boolean;
  rule_id: string | null;
  rule_version: number | null;
  source_reference: string | null;
  active: boolean;
  assigned_to?: string | null;
  reviewer_id?: string | null;
  readiness_status: ReadinessStatus;
  readiness_details?: ReadinessResult | null;
  completed_at?: string | null;
  approved_at?: string | null;
  review_notes?: string | null;
  prerequisite_config?: Record<string, unknown> | null;
  is_overdue: boolean;
  days_overdue?: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ComplianceObligationEvidence {
  id: string;
  obligation_id: string;
  company_id: string;
  document_id: string;
  description: string | null;
  document?: {
    original_filename?: string;
  };
  created_by: string;
  created_at: string;
}

export interface ComplianceHealth {
  health_status: ComplianceHealthStatus;
  status: ComplianceHealthStatus;
  score: number;
  summary: string;
  reasons: string[];
  dimensions: {
    overdue_obligations: number;
    overdue_tasks: number;
    total_overdue: number;
    blocked_obligations: number;
    due_soon_obligations: number;
    pending_reviews: number;
    critical_audit_findings: number;
    unmatched_bank_transactions: number;
    unallocated_tds_transactions: number;
  };
  breakdown: {
    overdue_obligations: number;
    blocked_obligations: number;
    missing_prerequisites: number;
    pending_reviews: number;
    unresolved_audit_findings: number;
    unreconciled_bank_items: number;
  };
}

export interface ComplianceControlCenterSummary {
  total_obligations: number;
  due_soon: number;
  overdue: number;
  blocked: number;
  awaiting_review: number;
  awaiting_review_count?: number;
  completed: number;
  health: ComplianceHealth;
  overdue_obligations?: ComplianceObligation[];
  blocked_obligations?: ComplianceObligation[];
  awaiting_review_obligations?: ComplianceObligation[];
  upcoming_obligations?: ComplianceObligation[];
}

export interface Notification {
  id: string;
  company_id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  severity: NotificationSeverity;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
}

export interface ComplianceTask {
  id: string;
  company_id: string;
  obligation_id: string | null;
  title: string;
  description: string | null;
  category: ComplianceCategory;
  module: ComplianceModule;
  status: ComplianceTaskStatus;
  priority: CompliancePriority;
  assigned_to: string | null;
  reviewer_id: string | null;
  start_date: string | null;
  due_date: string;
  completed_at: string | null;
  verified_at: string | null;
  source_type: ComplianceSourceType;
  source_id: string | null;
  completion_notes: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
}

export interface ComplianceTaskComment {
  id: string;
  task_id: string;
  user_id: string;
  comment: string;
  created_at: string;
}

export interface ComplianceTaskEvidence {
  id: string;
  task_id: string;
  document_id: string;
  description: string | null;
  created_by: string;
  created_at: string;
}

export interface CalendarItem {
  task_id?: string | null;
  obligation_id?: string | null;
  item_type: "TASK" | "OBLIGATION";
  title: string;
  category: ComplianceCategory;
  priority: CompliancePriority;
  status: string;
  is_overdue: boolean;
}

export interface CalendarDay {
  date: string;
  items: CalendarItem[];
}

export interface ComplianceDashboard {
  total_open: number;
  due_today: number;
  due_this_week: number;
  overdue: number;
  pending_review: number;
  completed: number;
  verified: number;
  critical_tasks: number;
  by_category: Record<ComplianceCategory, number>;
  by_priority: Record<CompliancePriority, number>;
}
