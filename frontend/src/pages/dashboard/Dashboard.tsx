import { Link, useNavigate } from "react-router-dom";
import {
  Building2,
  ScrollText,
  Users,
  ArrowUpRight,
  Landmark,
  FileText,
  GitMerge,
  ShieldCheck,
  Calculator,
  Banknote,
  CalendarClock,
  ClipboardCheck,
  Plus,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useCompanies } from "@/hooks/useCompanies";
import { useCompanyUsers } from "@/hooks/useCompanyUsers";
import { useAuditLogs } from "@/hooks/useAuditLogs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/utils";

const MODULE_PLACEHOLDERS = [
  { title: "Documents", subtitle: "Upload & OCR Ingestion", icon: FileText, to: "/documents" },
  { title: "Accounting", subtitle: "Ledgers, FY & Double-Entry", icon: Landmark, to: "/accounting/dashboard" },
  { title: "GST Compliance", subtitle: "GSTR-1, 3B & 2B Recon", icon: ShieldCheck, to: "/gst" },
  { title: "TDS Compliance", subtitle: "26Q, 27Q, Rules & Challans", icon: Calculator, to: "/tds" },
  { title: "Bank Reconciliation", subtitle: "Rule-based & Auto Matching", icon: GitMerge, to: "/bank" },
  { title: "Income Tax", subtitle: "Slabs, Relief & Computations", icon: Banknote, to: "/income-tax" },
  { title: "Compliance Calendar", subtitle: "Due Dates, Tasks & Alerts", icon: CalendarClock, to: "/compliance/calendar" },
  { title: "Audit Engagements", subtitle: "Auditor Workflow & Findings", icon: ClipboardCheck, to: "/audits" },
];

export default function DashboardPage() {
  const { user, activeCompany, companies } = useAuth();
  const navigate = useNavigate();
  const { data: companiesData, isLoading: companiesLoading } = useCompanies(1, 1);
  const { data: usersData, isLoading: usersLoading } = useCompanyUsers(activeCompany?.company_id, 1, 1);
  const { data: auditData, isLoading: auditLoading } = useAuditLogs(
    activeCompany ? { companyId: activeCompany.company_id, pageSize: 5 } : null
  );

  const hasCompanies = (companiesData?.pagination.total ?? 0) > 0 || companies.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Welcome back, {user?.first_name}
          </h1>
          <p className="text-sm text-muted-foreground">
            Here&apos;s an overview of your compliance and accounting workspaces.
          </p>
        </div>
        {!activeCompany && (
          <Button onClick={() => navigate(hasCompanies ? "/companies" : "/companies?create=true")} className="gap-2">
            {hasCompanies ? <Building2 className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {hasCompanies ? "Select Company" : "Create Company"}
          </Button>
        )}
      </div>

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
        <Card className="border-border bg-muted/20">
          <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground">{activeCompany.company_name}</span>
                <Badge variant="success" className="text-xs">Active Workspace</Badge>
                <Badge variant="outline" className="text-xs">{activeCompany.role_name}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Standard Indian FY and 13 Chart of Accounts ledgers are initialized and ready for transaction posting.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => navigate("/accounting/sales-invoices/new")} className="gap-1.5">
                <Plus className="h-3.5 w-3.5" /> Sales Invoice
              </Button>
              <Button size="sm" variant="outline" onClick={() => navigate("/accounting/purchase-invoices/new")} className="gap-1.5">
                <Plus className="h-3.5 w-3.5" /> Purchase Invoice
              </Button>
              <Button size="sm" variant="outline" onClick={() => navigate("/documents")} className="gap-1.5">
                <FileText className="h-3.5 w-3.5" /> Upload Document
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          title="Current Company"
          value={activeCompany?.company_name ?? "None selected"}
          icon={Building2}
        />
        <SummaryCard title="Your Role" value={activeCompany?.role_name ?? "—"} icon={ShieldCheck} />
        <SummaryCard
          title="Companies"
          value={companiesLoading ? undefined : String(companiesData?.pagination.total ?? 0)}
          icon={Building2}
        />
        <SummaryCard
          title="Users in Company"
          value={usersLoading ? undefined : String(usersData?.pagination.total ?? 0)}
          icon={Users}
        />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Compliance Modules
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {MODULE_PLACEHOLDERS.map((m) => {
            const card = (
              <Card className="transition-all hover:border-primary/40 hover:shadow-xs cursor-pointer">
                <CardContent className="flex flex-col gap-3 pt-6">
                  <div className="flex items-center justify-between">
                    <m.icon className="h-5 w-5 text-primary" />
                    <Badge variant="success">Available</Badge>
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">{m.title}</p>
                    <p className="text-xs text-muted-foreground">{m.subtitle}</p>
                  </div>
                </CardContent>
              </Card>
            );
            return (
              <Link key={m.title} to={m.to}>
                {card}
              </Link>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent activity</CardTitle>
              <CardDescription>Latest actions in your active company</CardDescription>
            </div>
            <Link
              to="/audit-logs"
              className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              View all <ArrowUpRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardContent>
            {!activeCompany ? (
              <EmptyState message="Select a company to see recent activity." />
            ) : auditLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : auditData?.items.length ? (
              <ul className="divide-y divide-border">
                {auditData.items.map((log) => (
                  <li key={log.id} className="flex items-center justify-between py-3 text-sm">
                    <div className="flex items-center gap-2">
                      <ScrollText className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{log.action.replace(/_/g, " ")}</span>
                      {log.description && (
                        <span className="text-muted-foreground">— {log.description}</span>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(log.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState message="No activity recorded yet." />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick actions</CardTitle>
            <CardDescription>Jump to common tasks</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <QuickAction to="/documents" label="Upload a document" icon={FileText} />
            <QuickAction to="/accounting/sales-invoices/new" label="Create sales invoice" icon={Landmark} />
            <QuickAction to="/companies" label="View companies" icon={Building2} />
            <QuickAction to="/audits" label="Audit engagements" icon={ClipboardCheck} />
            <QuickAction to="/compliance/calendar" label="Compliance calendar" icon={CalendarClock} />
            <QuickAction to="/audit-logs" label="Review audit logs" icon={ScrollText} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  value,
  icon: Icon,
}: {
  title: string;
  value: string | undefined;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{title}</p>
          {value === undefined ? (
            <Skeleton className="mt-1 h-5 w-20" />
          ) : (
            <p className="truncate text-lg font-semibold">{value}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function QuickAction({
  to,
  label,
  icon: Icon,
}: {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
    >
      <Icon className="h-4 w-4 text-muted-foreground" />
      {label}
    </Link>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-8 text-center text-sm text-muted-foreground">
      <ScrollText className="h-6 w-6" />
      {message}
    </div>
  );
}
