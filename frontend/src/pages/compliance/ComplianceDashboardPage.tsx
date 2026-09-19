import { Link } from "react-router-dom";
import { CalendarClock } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useComplianceDashboard } from "@/hooks/useComplianceCalendar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyCompanyState } from "@/pages/accounting/LedgersPage";
import type { CompliancePriority } from "@/types/compliance";

const PRIORITY_VARIANT: Record<CompliancePriority, "secondary" | "warning" | "destructive"> = {
  LOW: "secondary",
  MEDIUM: "secondary",
  HIGH: "warning",
  CRITICAL: "destructive",
};

export default function ComplianceDashboardPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={CalendarClock} />;
  const companyId = activeCompany.company_id;

  const { data, isLoading } = useComplianceDashboard(companyId);

  const cards: [string, number][] = data
    ? [
        ["Total Open", data.total_open],
        ["Due Today", data.due_today],
        ["Due This Week", data.due_this_week],
        ["Overdue", data.overdue],
        ["Pending Review", data.pending_review],
        ["Completed", data.completed],
        ["Verified", data.verified],
        ["Critical", data.critical_tasks],
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Compliance</h1>
          <p className="text-sm text-muted-foreground">
            One place to see what compliance work is due, who owns it, and what's overdue.
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/compliance/calendar" className="text-sm font-medium text-primary hover:underline">Calendar</Link>
          <Link to="/compliance/tasks" className="text-sm font-medium text-primary hover:underline">Tasks</Link>
        </div>
      </div>

      {isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {cards.map(([label, value]) => (
            <Card key={label}>
              <CardContent className="pt-6">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
                <p className="mt-1 text-lg font-semibold">{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Card>
            <CardContent className="pt-6">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">By Category</h2>
              <div className="space-y-2">
                {Object.entries(data.by_category)
                  .filter(([, count]) => count > 0)
                  .map(([category, count]) => (
                    <div key={category} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{category.replaceAll("_", " ")}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">By Priority</h2>
              <div className="space-y-2">
                {(Object.entries(data.by_priority) as [CompliancePriority, number][])
                  .filter(([, count]) => count > 0)
                  .map(([priority, count]) => (
                    <div key={priority} className="flex items-center justify-between text-sm">
                      <Badge variant={PRIORITY_VARIANT[priority]}>{priority}</Badge>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
