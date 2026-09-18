import { Link } from "react-router-dom";
import { Building2, ScrollText, Users, ArrowUpRight, Landmark, FileText, GitMerge, ShieldCheck, Calculator } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useCompanies } from "@/hooks/useCompanies";
import { useCompanyUsers } from "@/hooks/useCompanyUsers";
import { useAuditLogs } from "@/hooks/useAuditLogs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/utils";

const MODULE_PLACEHOLDERS = [
  { title: "Documents", subtitle: "Available now", icon: FileText, status: "available" as const, to: "/documents" },
  { title: "Accounting", subtitle: "Available now", icon: Landmark, status: "available" as const, to: "/accounting/dashboard" },
  { title: "GST Compliance", subtitle: "Available now", icon: ShieldCheck, status: "available" as const, to: "/gst" },
  { title: "TDS Compliance", subtitle: "Available now", icon: Calculator, status: "available" as const, to: "/tds" },
  { title: "Bank Reconciliation", subtitle: "Coming in a future phase", icon: GitMerge, status: "planned" as const, to: null },
  { title: "Audit", subtitle: "Foundation available", icon: ShieldCheck, status: "available" as const, to: "/audit-logs" },
];

export default function DashboardPage() {
  const { user, activeCompany } = useAuth();
  const { data: companiesData, isLoading: companiesLoading } = useCompanies(1, 1);
  const { data: usersData, isLoading: usersLoading } = useCompanyUsers(activeCompany?.company_id, 1, 1);
  const { data: auditData, isLoading: auditLoading } = useAuditLogs(
    activeCompany ? { companyId: activeCompany.company_id, pageSize: 5 } : null
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Welcome back, {user?.first_name}
        </h1>
        <p className="text-sm text-muted-foreground">
          Here&apos;s what&apos;s happening in your compliance workspace.
        </p>
      </div>

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
              <Card className={m.to ? "transition-colors hover:border-primary/40" : undefined}>
                <CardContent className="flex flex-col gap-3 pt-6">
                  <div className="flex items-center justify-between">
                    <m.icon className="h-5 w-5 text-muted-foreground" />
                    <Badge variant={m.status === "available" ? "success" : "secondary"}>
                      {m.status === "available" ? "Available" : "Planned"}
                    </Badge>
                  </div>
                  <div>
                    <p className="font-medium">{m.title}</p>
                    <p className="text-xs text-muted-foreground">{m.subtitle}</p>
                  </div>
                </CardContent>
              </Card>
            );
            return m.to ? (
              <Link key={m.title} to={m.to}>{card}</Link>
            ) : (
              <div key={m.title}>{card}</div>
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
            <QuickAction to="/companies" label="View companies" icon={Building2} />
            <QuickAction to="/users" label="Manage users" icon={Users} />
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
