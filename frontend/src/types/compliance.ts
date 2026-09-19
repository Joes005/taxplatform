// Phase 9 — Compliance Calendar / Task Management / Notifications types.
// Same conventions as types/incomeTax.ts/types/audit.ts.

export type ComplianceCategory = "GST" | "TDS" | "INCOME_TAX" | "AUDIT" | "ACCOUNTING" | "BANK" | "GENERAL" | "OTHER";
export type ComplianceModule = "GST" | "TDS" | "INCOME_TAX" | "AUDIT" | "BANK_RECONCILIATION" | "ACCOUNTING" | "DOCUMENTS" | "GENERAL";
export type ComplianceFrequency = "MONTHLY" | "QUARTERLY" | "ANNUAL" | "ONE_TIME" | "CUSTOM";
export type CompliancePriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ComplianceObligationStatus = "ACTIVE" | "FULFILLED" | "CANCELLED";
export type ComplianceTaskStatus =
  | "PENDING" | "IN_PROGRESS" | "PENDING_REVIEW" | "COMPLETED" | "VERIFIED" | "OVERDUE" | "CANCELLED" | "LOCKED";
export type ComplianceSourceType =
  | "GST_RETURN" | "TDS_RETURN" | "INCOME_TAX_RETURN" | "AUDIT_ENGAGEMENT" | "AUDIT_CHECKLIST"
  | "BANK_RECONCILIATION" | "ACCOUNTING_PERIOD" | "DOCUMENT" | "MANUAL";
export type NotificationType =
  | "TASK_ASSIGNED" | "TASK_DUE_SOON" | "TASK_OVERDUE" | "TASK_REVIEW_REQUIRED"
  | "TASK_COMPLETED" | "TASK_VERIFIED" | "COMMENT_ADDED" | "TASK_REASSIGNED";
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
  created_by: string;
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
  task_id: string;
  title: string;
  category: ComplianceCategory;
  priority: CompliancePriority;
  status: ComplianceTaskStatus;
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
