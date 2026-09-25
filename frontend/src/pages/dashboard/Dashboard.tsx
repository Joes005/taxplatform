import { useNavigate } from "react-router-dom";
import {
  Building2,
  Calendar,
  Clock,
  Plus,
  ShieldCheck,
  Sparkles,
  RotateCcw,
  CheckCircle2,
} from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useCompanies } from "@/hooks/useCompanies";
import {
  useDashboardSummary,
  useDashboardActions,
  useDashboardWorkflow,
  useDashboardSetupProgress,
  useDashboardHealth,
} from "@/hooks/useDashboard";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { AttentionCards } from "@/components/dashboard/AttentionCards";
import { WorkflowPipeline } from "@/components/dashboard/WorkflowPipeline";
import { SetupProgressCard } from "@/components/dashboard/SetupProgressCard";
import { CompanyHealthMatrix } from "@/components/dashboard/CompanyHealthMatrix";
import { ModuleActionsList } from "@/components/dashboard/ModuleActionsList";
import { RoleQuickActions } from "@/components/dashboard/RoleQuickActions";

export default function DashboardPage() {
  const { user, activeCompany, companies } = useAuth();
  const navigate = useNavigate();

  const companyId = activeCompany?.company_id;

  const { data: summary, isLoading: summaryLoading, refetch: refetchSummary } = useDashboardSummary(companyId);
  const { data: actions, isLoading: actionsLoading, refetch: refetchActions } = useDashboardActions(companyId);
  const { data: workflow, isLoading: workflowLoading, refetch: refetchWorkflow } = useDashboardWorkflow(companyId);
  const { data: setupProgress, isLoading: setupLoading, refetch: refetchSetup } = useDashboardSetupProgress(companyId);
  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useDashboardHealth(companyId);

  const { data: companiesData } = useCompanies(1, 1);
  const hasCompanies = (companiesData?.pagination.total ?? 0) > 0 || companies.length > 0;

  const handleRefreshAll = () => {
    refetchSummary();
    refetchActions();
    refetchWorkflow();
    refetchSetup();
    refetchHealth();
  };

  return (
    <div className="space-y-6">
      {/* Command Center Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              {user?.first_name ? `Welcome back, ${user.first_name}` : "Command Center"}
            </h1>
            {activeCompany && (
              <Badge variant="outline" className="text-xs font-mono">
                {activeCompany.role_name}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Unified operational cockpit: Real-time compliance health, workflow progression, and actionable alerts
          </p>
        </div>

        {activeCompany ? (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshAll}
              className="gap-1 text-xs h-8"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Refresh Data
            </Button>
            <Button
              size="sm"
              onClick={() => navigate("/action-center")}
              className="gap-1 text-xs h-8"
            >
              <ShieldCheck className="h-3.5 w-3.5" /> Action Center
            </Button>
          </div>
        ) : (
          <Button
            onClick={() => navigate(hasCompanies ? "/companies" : "/companies?create=true")}
            className="gap-2 h-8 text-xs"
          >
            {hasCompanies ? <Building2 className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {hasCompanies ? "Select Company" : "Create Company"}
          </Button>
        )}
      </div>

      {/* No Company Selected State */}
      {!activeCompany ? (
        <Card className="border-primary/20 bg-gradient-to-br from-primary/5 via-background to-background">
          <CardContent className="flex flex-col gap-6 p-8 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-3 max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                <Sparkles className="h-3.5 w-3.5" />
                Getting Started with Tally Tax
              </div>
              <h2 className="text-xl font-bold tracking-tight sm:text-2xl">
                {hasCompanies
                  ? "Select an active company workspace to begin"
                  : "Set up your organization in 30 seconds"}
              </h2>
              <p className="text-sm text-muted-foreground">
                {hasCompanies
                  ? "You have organization workspaces available. Choose one from your companies list or switcher to activate real-time GST, TDS, double-entry ledgers, and audit tools."
                  : "Creating your company automatically provisions a standard Indian Financial Year (April–March) and seeds 13 core Chart of Accounts ledgers (Cash, Bank, Debtors, Creditors, GST Input/Output)."}
              </p>
              <div className="flex flex-wrap gap-4 pt-1 text-xs font-medium text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-primary" /> Auto Indian FY
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-primary" /> 13 Seeded Ledgers
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-primary" /> Automatic Double-Entry
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-primary" /> Multi-Tenant RBAC
                </span>
              </div>
            </div>
            <div className="shrink-0">
              {hasCompanies ? (
                <Button size="lg" onClick={() => navigate("/companies")} className="gap-2">
                  <Building2 className="h-5 w-5" />
                  View Companies
                </Button>
              ) : (
                <Button size="lg" onClick={() => navigate("/companies?create=true")} className="gap-2">
                  <Plus className="h-5 w-5" />
                  Create Your Company
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Active Company Metadata Strip */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-2.5 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <Building2 className="h-4 w-4 text-primary" />
                {summary?.company_name || activeCompany.company_name}
              </span>
              <span className="text-muted-foreground">•</span>
              <span className="flex items-center gap-1 text-muted-foreground">
                <Calendar className="h-3.5 w-3.5" />
                FY: <strong className="text-foreground">{summary?.financial_year || "2025-2026"}</strong>
              </span>
              <span className="text-muted-foreground">•</span>
              <span className="text-muted-foreground">
                Period: <strong className="text-foreground">{summary?.active_period || "Q4 (Jan-Mar)"}</strong>
              </span>
            </div>

            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="h-3.5 w-3.5" />
              <span>Last update: {summary?.last_data_update ? new Date(summary.last_data_update).toLocaleTimeString() : "Live"}</span>
            </div>
          </div>

          {/* Attention Summary Cards */}
          <AttentionCards attention={summary?.attention} isLoading={summaryLoading} />

          {/* Setup / Onboarding Progress */}
          <SetupProgressCard progress={setupProgress} isLoading={setupLoading} />

          {/* Visual Workflow Pipeline */}
          <WorkflowPipeline stages={workflow} isLoading={workflowLoading} />

          {/* Company Health Matrix */}
          <CompanyHealthMatrix health={health} isLoading={healthLoading} />

          {/* Two-Column: Today's Actions & Role Quick Action Hub */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <ModuleActionsList actions={actions} isLoading={actionsLoading} />
            </div>

            <div className="space-y-6">
              <RoleQuickActions role={activeCompany.role_name} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
