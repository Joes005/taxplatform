import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, ChevronDown, ChevronUp, Sparkles, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { SetupProgress } from "@/types/dashboard";

interface SetupProgressCardProps {
  progress?: SetupProgress;
  isLoading: boolean;
}

export function SetupProgressCard({ progress, isLoading }: SetupProgressCardProps) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);

  if (isLoading) {
    return <Skeleton className="h-28 w-full rounded-xl" />;
  }

  if (!progress) return null;

  const percentage = Math.round((progress.completed_count / progress.total_count) * 100);

  // If 100% complete, show a compact congratulatory banner with expand option
  return (
    <Card className="border-primary/20 bg-gradient-to-r from-primary/5 via-background to-background">
      <CardContent className="p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Sparkles className="h-3.5 w-3.5" />
              </span>
              <h3 className="text-sm font-semibold text-foreground">
                Company Onboarding & Setup Progress
              </h3>
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                {progress.completed_count} of {progress.total_count} Complete ({percentage}%)
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {progress.is_all_complete
                ? "All critical organization configurations are complete and verified!"
                : "Complete remaining prerequisite configurations to enable full tax calculations and reports."}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="w-32 bg-muted rounded-full h-2 overflow-hidden">
              <div
                className="bg-primary h-full transition-all duration-500 rounded-full"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              className="h-8 gap-1 text-xs"
            >
              {expanded ? "Hide Details" : "View Steps"}
              {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </div>

        {expanded && (
          <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {progress.steps.map((step) => (
              <div
                key={step.key}
                className={`flex items-start justify-between rounded-lg border p-3 ${
                  step.completed
                    ? "border-emerald-500/30 bg-emerald-500/5"
                    : "border-border bg-card hover:border-primary/40"
                }`}
              >
                <div className="space-y-1 pr-2">
                  <div className="flex items-center gap-1.5">
                    {step.completed ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                    ) : (
                      <span className="h-2 w-2 rounded-full bg-amber-500 shrink-0" />
                    )}
                    <span className="text-xs font-medium text-foreground">{step.label}</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground line-clamp-2">
                    {step.description}
                  </p>
                </div>
                {!step.completed && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => navigate(step.target_url)}
                    className="h-7 px-2 text-xs text-primary shrink-0 hover:bg-primary/10"
                  >
                    Setup <ArrowRight className="h-3 w-3 ml-1" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
