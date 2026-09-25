import { useNavigate } from "react-router-dom";
import { CheckCircle2, AlertTriangle, AlertCircle, Circle, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { WorkflowStage } from "@/types/dashboard";

interface WorkflowPipelineProps {
  stages?: WorkflowStage[];
  isLoading: boolean;
}

export function WorkflowPipeline({ stages, isLoading }: WorkflowPipelineProps) {
  const navigate = useNavigate();

  const getStatusBadge = (status: WorkflowStage["status"]) => {
    switch (status) {
      case "COMPLETE":
        return (
          <Badge variant="success" className="gap-1 text-[10px]">
            <CheckCircle2 className="h-3 w-3" /> Complete
          </Badge>
        );
      case "IN_PROGRESS":
        return (
          <Badge variant="secondary" className="gap-1 text-[10px] text-amber-600 bg-amber-500/10 border-amber-500/20">
            <AlertCircle className="h-3 w-3" /> In Progress
          </Badge>
        );
      case "BLOCKED":
        return (
          <Badge variant="destructive" className="gap-1 text-[10px]">
            <AlertTriangle className="h-3 w-3" /> Blocked
          </Badge>
        );
      case "NOT_STARTED":
      default:
        return (
          <Badge variant="outline" className="gap-1 text-[10px] text-muted-foreground">
            <Circle className="h-3 w-3" /> Not Started
          </Badge>
        );
    }
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <div>
            <CardTitle className="text-base font-semibold">Workflow Lifecycle Pipeline</CardTitle>
            <CardDescription className="text-xs">
              End-to-end business lifecycle from raw documents to audited tax compliance and reporting
            </CardDescription>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-emerald-500" /> Complete
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-amber-500" /> In Progress
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-red-500" /> Blocked
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full rounded-lg" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-8">
            {stages?.map((stage, idx) => (
              <div
                key={stage.stage_key}
                className="group relative flex flex-col justify-between rounded-lg border border-border bg-card p-3 transition-all hover:border-primary/40 hover:shadow-xs"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold text-muted-foreground">0{idx + 1}</span>
                    {getStatusBadge(stage.status)}
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-foreground truncate" title={stage.name}>
                      {stage.name}
                    </h4>
                    <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                      {stage.blocking_count > 0 ? (
                        <span className="text-red-500 font-medium">
                          {stage.blocking_count} blocked
                        </span>
                      ) : stage.pending_count > 0 ? (
                        <span className="text-amber-600 font-medium">
                          {stage.pending_count} pending
                        </span>
                      ) : (
                        <span className="text-emerald-600 font-medium">Up to date</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-border/50">
                  {stage.next_action_url && stage.next_action_label ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(stage.next_action_url!)}
                      className="h-7 w-full justify-between px-2 text-[11px] font-medium text-primary hover:bg-primary/10"
                    >
                      <span className="truncate">{stage.next_action_label}</span>
                      <ArrowRight className="h-3 w-3 shrink-0 ml-1" />
                    </Button>
                  ) : (
                    <span className="block text-[11px] text-center text-muted-foreground py-1">Ready</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
