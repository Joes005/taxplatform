import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type {
  DashboardSummary,
  DashboardActionItem,
  WorkflowStage,
  SetupProgress,
  CompanyHealth,
  ActionCenterItem,
} from "@/types/dashboard";

export interface ActionCenterParams {
  category?: string;
  severity?: string;
  module_name?: string;
  page?: number;
  page_size?: number;
}

export const dashboardService = {
  getSummary: (companyId: string) =>
    apiClient.get<DashboardSummary>(`/dashboard/summary?company_id=${companyId}`),

  getActions: (companyId: string) =>
    apiClient.get<DashboardActionItem[]>(`/dashboard/actions?company_id=${companyId}`),

  getWorkflow: (companyId: string) =>
    apiClient.get<WorkflowStage[]>(`/dashboard/workflow?company_id=${companyId}`),

  getSetupProgress: (companyId: string) =>
    apiClient.get<SetupProgress>(`/dashboard/setup-progress?company_id=${companyId}`),

  getHealth: (companyId: string) =>
    apiClient.get<CompanyHealth>(`/dashboard/health?company_id=${companyId}`),

  getActionCenter: (companyId: string, params: ActionCenterParams = {}) => {
    const searchParams = new URLSearchParams({ company_id: companyId });
    if (params.category && params.category !== "ALL") searchParams.set("category", params.category);
    if (params.severity && params.severity !== "ALL") searchParams.set("severity", params.severity);
    if (params.module_name && params.module_name !== "ALL") searchParams.set("module_name", params.module_name);
    if (params.page) searchParams.set("page", params.page.toString());
    if (params.page_size) searchParams.set("page_size", params.page_size.toString());
    return apiClient.get<PaginatedData<ActionCenterItem>>(`/action-center?${searchParams.toString()}`);
  },
};
