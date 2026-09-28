import { RefreshCw, ShieldAlert, ShieldCheck, AlertTriangle } from "lucide-react";
import { useComplianceHealth } from "@/hooks/useComplianceObligations";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ComplianceHealthStatus } from "@/types/compliance";

const STATUS_CONFIG: Record<
  ComplianceHealthStatus,
  { label: string; variant: "success" | "warning" | "destructive" | "secondary"; icon: typeof ShieldCheck }
> = {
  HEALTHY: { label: "Healthy", variant: "success", icon: ShieldCheck },
  ATTENTION_REQUIRED: { label: "Attention Required", variant: "warning", icon: AlertTriangle },
  AT_RISK: { label: "At Risk", variant: "warning", icon: ShieldAlert },
  OVERDUE: { label: "Overdue", variant: "destructive", icon: ShieldAlert },
};

interface ComplianceHealthCardProps {
  companyId: string;
}

export function ComplianceHealthCard({ companyId }: ComplianceHealthCardProps) {
  const { data: health, isLoading, refetch, isFetching } = useComplianceHealth(companyId);

  if (isLoading) {
    return <Skeleton className="h-44 w-full rounded-xl" />;
  }

  if (!health) return null;

  const config = STATUS_CONFIG[health.status] || {
    label: health.status,
    variant: "secondary" as const,
    icon: ShieldCheck,
  };
  const StatusIcon = config.icon;

  return (
    <Card className="border-border shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base font-semibold">Compliance Health</CardTitle>
            <Badge variant={config.variant} className="flex items-center gap-1">
              <StatusIcon className="h-3.5 w-3.5" />
              <span>{config.label}</span>
            </Badge>
          </div>
          <CardDescription className="text-xs">
            Deterministic evaluation of cross-module compliance obligations, prerequisites, and pending audits.
          </CardDescription>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-2xl font-bold">{health.score}</span>
            <span className="text-xs text-muted-foreground"> / 100</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            title="Recalculate compliance health"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-2">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-6">
          <div className="rounded-md border border-border p-2 text-center bg-card">
            <div className="text-xs text-muted-foreground">Overdue</div>
            <div className={`text-base font-bold ${health.breakdown.overdue_obligations > 0 ? "text-destructive" : ""}`}>
              {health.breakdown.overdue_obligations}
            </div>
          </div>
          <div className="rounded-md border border-border p-2 text-center bg-card">
            <div className="text-xs text-muted-foreground">Blocked</div>
            <div className={`text-base font-bold ${health.breakdown.blocked_obligations > 0 ? "text-amber-500" : ""}`}>
              {health.breakdown.blocked_obligations}
            </div>
          </div>
          <div className="rounded-md border border-border p-2 text-center bg-card">
            <div className="text-xs text-muted-foreground">Missing Prereq</div>
            <div className={`text-base font-bold ${health.breakdown.missing_prerequisites > 0 ? "text-amber-500" : ""}`}>
              {health.breakdown.missing_prerequisites}
            </div>
          </div>
          <div className="rounded-md border border-border p-2 text-center bg-card">
            <div className="text-xs text-muted-foreground">Pending Review</div>
            <div className="text-base font-bold text-foreground">
              {health.breakdown.pending_reviews}
            </div>
          </div>
          <div className="rounded-md border border-border p-2 text-center bg-card">
            <div className="text-xs text-muted-foreground">Audit Findings</div>
            <div className={`text-base font-bold ${health.breakdown.unresolved_audit_findings > 0 ? "text-amber-500" : ""}`}>
              {health.breakdown.unresolved_audit_findings}
            </div>
          </div>
          <div className="rounded-md border border-border p-2 text-center bg-card">
            <div className="text-xs text-muted-foreground">Unreconciled Bank</div>
            <div className={`text-base font-bold ${health.breakdown.unreconciled_bank_items > 0 ? "text-amber-500" : ""}`}>
              {health.breakdown.unreconciled_bank_items}
            </div>
          </div>
        </div>

        {health.reasons.length > 0 && (
          <div className="rounded-lg bg-muted/40 p-3 text-xs space-y-1.5 border border-border/50">
            <div className="font-semibold text-muted-foreground uppercase tracking-wider text-[10px]">
              Compliance Health Impact Factors
            </div>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              {health.reasons.map((reason, idx) => (
                <li key={idx} className="leading-snug">
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
