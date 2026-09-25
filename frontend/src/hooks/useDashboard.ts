import { useQuery } from "@tanstack/react-query";
import { dashboardService, type ActionCenterParams } from "@/services/dashboardService";

export const dashboardKeys = {
  all: (companyId: string) => ["dashboard", companyId] as const,
  summary: (companyId: string) => ["dashboard", companyId, "summary"] as const,
  actions: (companyId: string) => ["dashboard", companyId, "actions"] as const,
  workflow: (companyId: string) => ["dashboard", companyId, "workflow"] as const,
  setupProgress: (companyId: string) => ["dashboard", companyId, "setup-progress"] as const,
  health: (companyId: string) => ["dashboard", companyId, "health"] as const,
  actionCenter: (companyId: string, params: ActionCenterParams) =>
    ["action-center", companyId, params] as const,
};

export function useDashboardSummary(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? dashboardKeys.summary(companyId) : ["dashboard", "none", "summary"],
    queryFn: () => dashboardService.getSummary(companyId as string),
    enabled: !!companyId,
    refetchInterval: 30_000,
  });
}

export function useDashboardActions(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? dashboardKeys.actions(companyId) : ["dashboard", "none", "actions"],
    queryFn: () => dashboardService.getActions(companyId as string),
    enabled: !!companyId,
  });
}

export function useDashboardWorkflow(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? dashboardKeys.workflow(companyId) : ["dashboard", "none", "workflow"],
    queryFn: () => dashboardService.getWorkflow(companyId as string),
    enabled: !!companyId,
  });
}

export function useDashboardSetupProgress(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? dashboardKeys.setupProgress(companyId) : ["dashboard", "none", "setup-progress"],
    queryFn: () => dashboardService.getSetupProgress(companyId as string),
    enabled: !!companyId,
  });
}

export function useDashboardHealth(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? dashboardKeys.health(companyId) : ["dashboard", "none", "health"],
    queryFn: () => dashboardService.getHealth(companyId as string),
    enabled: !!companyId,
  });
}

export function useActionCenter(companyId: string | undefined, params: ActionCenterParams = {}) {
  return useQuery({
    queryKey: companyId ? dashboardKeys.actionCenter(companyId, params) : ["action-center", "none"],
    queryFn: () => dashboardService.getActionCenter(companyId as string, params),
    enabled: !!companyId,
  });
}
