import { useState } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/useToast";
import { useRunObligationReadiness } from "@/hooks/useComplianceObligations";
import { ComplianceReadinessBadge } from "./ComplianceStatusBadge";
import type { ComplianceObligation, ReadinessCheckDetail, ReadinessStatus } from "@/types/compliance";

interface ReadinessCheckDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  companyId: string;
  obligation: ComplianceObligation | null;
}

const MODULE_ROUTES: Record<string, string> = {
  GST: "/gst",
  TDS: "/tds",
  INCOME_TAX: "/income-tax",
  BANK: "/bank",
  AUDIT: "/audits",
  ACCOUNTING: "/accounting/ledgers",
};

export function ReadinessCheckDialog({
  open,
  onOpenChange,
  companyId,
  obligation,
}: ReadinessCheckDialogProps) {
  const { toast } = useToast();
  const runReadiness = useRunObligationReadiness(companyId);
  const [latestResult, setLatestResult] = useState<{
    status: ReadinessStatus;
    summary: string;
    checks: ReadinessCheckDetail[];
    blocking_failures: string[];
    warnings: string[];
  } | null>(null);

  if (!obligation) return null;

  const currentStatus: ReadinessStatus =
    latestResult?.status || obligation.readiness_status || "NOT_APPLICABLE";
  const checks: ReadinessCheckDetail[] =
    latestResult?.checks || (obligation.readiness_details?.checks as ReadinessCheckDetail[]) || [];
  const blockingFailures: string[] =
    latestResult?.blocking_failures ||
    checks.filter((c) => c.blocking && c.status === "FAIL").map((c) => c.check_code);

  const handleEvaluate = async () => {
    try {
      const res = await runReadiness.mutateAsync(obligation.id);
      const fails = res.checks.filter((c) => c.blocking && c.status === "FAIL").map((c) => c.check_code);
      setLatestResult({
        status: res.overall_status,
        summary: `Status: ${res.overall_status}`,
        checks: res.checks,
        blocking_failures: fails,
        warnings: res.checks.filter((c) => c.status === "WARN").map((c) => c.description),
      });
      toast({
        title: "Readiness evaluated",
        description: `Status: ${res.overall_status.replaceAll("_", " ")}`,
        variant: res.overall_status === "BLOCKED" ? "destructive" : "success",
      });
    } catch {
      toast({
        title: "Evaluation failed",
        description: "Could not evaluate compliance prerequisites.",
        variant: "destructive",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between pr-6">
            <div className="flex items-center gap-2">
              <DialogTitle className="text-lg font-semibold">Prerequisite Readiness Check</DialogTitle>
              <ComplianceReadinessBadge status={currentStatus} />
            </div>
          </div>
          <DialogDescription className="text-xs">
            Evaluates upstream accounting, tax computations, reconciliation, and audit prerequisites for{" "}
            <span className="font-semibold text-foreground">{obligation.name}</span> ({obligation.code}).
          </DialogDescription>
        </DialogHeader>

        {blockingFailures.length > 0 && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive flex items-start gap-2">
            <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold">Blocking Prerequisites Found</div>
              <p className="mt-0.5">
                This obligation cannot be approved or completed until the following blocking issues are resolved:
              </p>
              <ul className="list-disc list-inside mt-1 font-mono text-[11px]">
                {blockingFailures.map((code) => (
                  <li key={code}>{code}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Checklist Items ({checks.length})
            </h4>
            <Button
              variant="outline"
              size="sm"
              onClick={handleEvaluate}
              disabled={runReadiness.isPending}
              className="h-7 text-xs flex items-center gap-1.5"
            >
              <RefreshCw className={`h-3 w-3 ${runReadiness.isPending ? "animate-spin" : ""}`} />
              Re-run Checks
            </Button>
          </div>

          {checks.length === 0 ? (
            <div className="rounded-md border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
              No detailed checks evaluated yet. Click &quot;Re-run Checks&quot; to evaluate prerequisites.
            </div>
          ) : (
            <div className="space-y-2">
              {checks.map((check, idx) => {
                const isPass = check.status === "PASS";
                const isFail = check.status === "FAIL";
                const isWarn = check.status === "WARN";
                const moduleRoute = MODULE_ROUTES[check.source_module];

                return (
                  <div
                    key={`${check.check_code}-${idx}`}
                    className={`rounded-lg border p-3 text-xs transition-colors ${
                      isFail && check.blocking
                        ? "border-destructive/40 bg-destructive/5"
                        : isWarn
                        ? "border-amber-500/30 bg-amber-500/5"
                        : "border-border bg-card"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2">
                        {isPass ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                        ) : isFail ? (
                          <XCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                        ) : isWarn ? (
                          <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                        ) : (
                          <HelpCircle className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                        )}
                        <div>
                          <div className="font-medium text-foreground flex items-center gap-2">
                            <span>{check.description}</span>
                            <Badge variant="outline" className="text-[10px] py-0 px-1.5">
                              {check.source_module}
                            </Badge>
                            {check.blocking && (
                              <Badge variant="destructive" className="text-[9px] py-0 px-1 uppercase tracking-wide">
                                Blocking
                              </Badge>
                            )}
                          </div>
                          {check.remediation_action && (
                            <div className="mt-1 text-muted-foreground">
                              <span className="font-semibold text-foreground/80">Remediation: </span>
                              {check.remediation_action}
                            </div>
                          )}
                          {check.entity_reference && (
                            <div className="mt-0.5 text-[10px] text-muted-foreground font-mono">
                              Ref: {check.entity_reference}
                            </div>
                          )}
                        </div>
                      </div>
                      {moduleRoute && (
                        <Button variant="ghost" size="sm" asChild className="h-6 text-xs px-2 shrink-0">
                          <Link to={moduleRoute} target="_blank" rel="noreferrer" className="flex items-center gap-1">
                            <span>Open</span>
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <DialogFooter className="mt-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
