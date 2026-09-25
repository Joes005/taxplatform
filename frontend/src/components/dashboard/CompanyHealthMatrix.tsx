import { useNavigate } from "react-router-dom";
import { CheckCircle2, AlertTriangle, AlertCircle, HelpCircle, ArrowUpRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { CompanyHealth, HealthAreaStatus } from "@/types/dashboard";

interface CompanyHealthMatrixProps {
  health?: CompanyHealth;
  isLoading: boolean;
}

export function CompanyHealthMatrix({ health, isLoading }: CompanyHealthMatrixProps) {
  const navigate = useNavigate();

  const getStatusBadge = (status: HealthAreaStatus["status"]) => {
    switch (status) {
      case "READY":
        return (
          <Badge variant="success" className="gap-1 text-[11px]">
            <CheckCircle2 className="h-3 w-3" /> Ready
          </Badge>
        );
      case "NEEDS_ATTENTION":
        return (
          <Badge variant="secondary" className="gap-1 text-[11px] text-amber-600 bg-amber-500/10 border-amber-500/20">
            <AlertCircle className="h-3 w-3" /> Needs Attention
          </Badge>
        );
      case "BLOCKED":
        return (
          <Badge variant="destructive" className="gap-1 text-[11px]">
            <AlertTriangle className="h-3 w-3" /> Blocked
          </Badge>
        );
      case "NOT_CONFIGURED":
      default:
        return (
          <Badge variant="outline" className="gap-1 text-[11px] text-muted-foreground">
            <HelpCircle className="h-3 w-3" /> Not Configured
          </Badge>
        );
    }
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <div>
            <CardTitle className="text-base font-semibold">System & Compliance Health Matrix</CardTitle>
            <CardDescription className="text-xs">
              Deterministic operational health evaluation across all 7 compliance domains
            </CardDescription>
          </div>
          {health && (
            <div>
              {getStatusBadge(health.overall_status)}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {Array.from({ length: 7 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full rounded-lg" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {health?.areas.map((area) => (
              <div
                key={area.area}
                className="flex flex-col justify-between rounded-lg border border-border bg-card p-3.5 transition-all hover:border-primary/40 hover:shadow-xs"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground">{area.area}</span>
                    {getStatusBadge(area.status)}
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {area.message}
                  </p>
                </div>

                <div className="mt-3 pt-2 border-t border-border/50 flex items-center justify-between">
                  <div className="text-[10px] text-muted-foreground">
                    {Object.entries(area.metrics).slice(0, 1).map(([k, v]) => (
                      <span key={k}>
                        {k.replace(/_/g, " ")}: <strong className="text-foreground">{v}</strong>
                      </span>
                    ))}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate(area.target_url)}
                    className="h-6 px-1.5 text-xs text-primary hover:bg-primary/10 gap-0.5"
                  >
                    Open <ArrowUpRight className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
