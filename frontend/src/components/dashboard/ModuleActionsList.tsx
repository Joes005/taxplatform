import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, AlertOctagon, AlertCircle, Clock, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { DashboardActionItem } from "@/types/dashboard";

interface ModuleActionsListProps {
  actions?: DashboardActionItem[];
  isLoading: boolean;
}

const MODULES = [
  "ALL",
  "GST",
  "TDS",
  "BANK",
  "ACCOUNTING",
  "INCOME_TAX",
  "AUDIT",
  "COMPLIANCE",
];

export function ModuleActionsList({ actions = [], isLoading }: ModuleActionsListProps) {
  const navigate = useNavigate();
  const [selectedModule, setSelectedModule] = useState<string>("ALL");

  const filteredActions = selectedModule === "ALL"
    ? actions
    : actions.filter((a) => a.module.toUpperCase() === selectedModule);

  const getSeverityBadge = (severity: DashboardActionItem["severity"]) => {
    switch (severity) {
      case "CRITICAL":
        return (
          <Badge variant="destructive" className="gap-1 text-[10px]">
            <AlertOctagon className="h-3 w-3" /> Critical
          </Badge>
        );
      case "HIGH":
        return (
          <Badge variant="secondary" className="gap-1 text-[10px] text-orange-600 bg-orange-500/10 border-orange-500/20">
            <AlertCircle className="h-3 w-3" /> High
          </Badge>
        );
      case "MEDIUM":
        return (
          <Badge variant="secondary" className="gap-1 text-[10px] text-amber-600 bg-amber-500/10 border-amber-500/20">
            <Clock className="h-3 w-3" /> Medium
          </Badge>
        );
      case "LOW":
      case "INFO":
      default:
        return (
          <Badge variant="outline" className="gap-1 text-[10px] text-blue-600 border-blue-500/20">
            Info
          </Badge>
        );
    }
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <CardTitle className="text-base font-semibold">Today&apos;s Actions &amp; Pending Tasks</CardTitle>
            <CardDescription className="text-xs">
              Context-aware, actionable tasks requiring your attention across all operational modules
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/action-center")}
            className="h-8 text-xs gap-1"
          >
            Open Action Center <ArrowRight className="h-3 w-3 ml-1" />
          </Button>
        </div>

        {/* Module Filter Tabs */}
        <div className="flex flex-wrap gap-1.5 pt-2">
          {MODULES.map((m) => {
            const count = m === "ALL"
              ? actions.length
              : actions.filter((a) => a.module.toUpperCase() === m).length;
            if (count === 0 && m !== "ALL") return null;

            return (
              <button
                key={m}
                onClick={() => setSelectedModule(m)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  selectedModule === m
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                {m.replace(/_/g, " ")} ({count})
              </button>
            );
          })}
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : filteredActions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center text-sm text-muted-foreground">
            <CheckCircle2 className="h-8 w-8 text-emerald-500 mb-2" />
            <p className="font-medium text-foreground">All caught up!</p>
            <p className="text-xs text-muted-foreground">
              No pending actions require attention in this module right now.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filteredActions.slice(0, 8).map((action) => (
              <div
                key={action.id}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between py-3 gap-2 group hover:bg-muted/30 px-2 rounded-md transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    {getSeverityBadge(action.severity)}
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {action.module}
                    </Badge>
                    <span className="text-sm font-semibold text-foreground">
                      {action.title}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {action.description}
                  </p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {action.due_date && (
                    <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" /> Due: {action.due_date}
                    </span>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigate(action.target_url)}
                    className="h-8 text-xs gap-1 group-hover:border-primary group-hover:text-primary"
                  >
                    Act Now <ArrowRight className="h-3 w-3" />
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
