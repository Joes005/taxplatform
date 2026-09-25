export interface AttentionSummary {
  critical_count: number;
  high_priority_count: number;
  due_soon_count: number;
  pending_review_count: number;
  overdue_count: number;
  completed_count: number;
}

export interface DashboardSummary {
  company_id: string;
  company_name: string;
  financial_year?: string | null;
  financial_year_id?: string | null;
  active_period?: string | null;
  last_data_update?: string | null;
  attention: AttentionSummary;
  role: string;
}

export interface DashboardActionItem {
  id: string;
  title: string;
  description: string;
  module: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  category: string;
  due_date?: string | null;
  created_date?: string | null;
  status: string;
  target_url: string;
  responsible_roles: string[];
  source_reference?: string | null;
}

export interface WorkflowStage {
  stage_key: string;
  name: string;
  status: "COMPLETE" | "IN_PROGRESS" | "BLOCKED" | "NOT_STARTED";
  pending_count: number;
  blocking_count: number;
  next_action_label?: string | null;
  next_action_url?: string | null;
}

export interface SetupStep {
  key: string;
  label: string;
  completed: boolean;
  description: string;
  target_url: string;
}

export interface SetupProgress {
  completed_count: number;
  total_count: number;
  is_all_complete: boolean;
  steps: SetupStep[];
}

export interface HealthAreaStatus {
  area: string;
  status: "READY" | "NEEDS_ATTENTION" | "BLOCKED" | "NOT_CONFIGURED";
  message: string;
  metrics: Record<string, string | number | boolean>;
  target_url: string;
}

export interface CompanyHealth {
  overall_status: "READY" | "NEEDS_ATTENTION" | "BLOCKED" | "NOT_CONFIGURED";
  areas: HealthAreaStatus[];
}

export interface ActionCenterItem {
  id: string;
  title: string;
  description: string;
  module: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  category: string;
  due_date?: string | null;
  created_date?: string | null;
  status: string;
  target_url: string;
  responsible_roles: string[];
  source_reference?: string | null;
}

export interface SearchResultItem {
  id: string;
  type: string;
  identifier: string;
  title: string;
  subtitle?: string | null;
  status?: string | null;
  date?: string | null;
  amount?: string | number | null;
  target_url: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  items: SearchResultItem[];
}
