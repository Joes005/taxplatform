import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarClock, ChevronLeft, ChevronRight } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useComplianceCalendarMonth } from "@/hooks/useComplianceCalendar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { EmptyCompanyState } from "@/pages/accounting/LedgersPage";
import type { CalendarDay, CompliancePriority } from "@/types/compliance";

const PRIORITY_VARIANT: Record<CompliancePriority, "secondary" | "warning" | "destructive"> = {
  LOW: "secondary",
  MEDIUM: "secondary",
  HIGH: "warning",
  CRITICAL: "destructive",
};

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function ComplianceCalendarPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={CalendarClock} />;
  const companyId = activeCompany.company_id;

  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1); // 1-12

  const { data, isLoading } = useComplianceCalendarMonth(companyId, year, month);

  const byDate = useMemo(() => {
    const map = new Map<string, CalendarDay>();
    (data ?? []).forEach((day) => map.set(day.date, day));
    return map;
  }, [data]);

  const firstOfMonth = new Date(year, month - 1, 1);
  const daysInMonth = new Date(year, month, 0).getDate();
  const leadingBlanks = firstOfMonth.getDay();
  const cells: (number | null)[] = [
    ...Array(leadingBlanks).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  const goToPreviousMonth = () => {
    if (month === 1) { setYear(year - 1); setMonth(12); } else { setMonth(month - 1); }
  };
  const goToNextMonth = () => {
    if (month === 12) { setYear(year + 1); setMonth(1); } else { setMonth(month + 1); }
  };

  const monthLabel = firstOfMonth.toLocaleDateString(undefined, { month: "long", year: "numeric" });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Compliance Calendar</h1>
          <p className="text-sm text-muted-foreground">Due dates for every open compliance task this month.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={goToPreviousMonth}><ChevronLeft className="h-4 w-4" /></Button>
          <span className="w-36 text-center text-sm font-medium">{monthLabel}</span>
          <Button size="sm" variant="outline" onClick={goToNextMonth}><ChevronRight className="h-4 w-4" /></Button>
        </div>
      </div>

      {isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-white">
          <div className="grid grid-cols-7 border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {WEEKDAYS.map((d) => <div key={d} className="p-2 text-center">{d}</div>)}
          </div>
          <div className="grid grid-cols-7">
            {cells.map((day, index) => {
              if (day === null) return <div key={`blank-${index}`} className="min-h-24 border-b border-r border-border bg-muted/10" />;
              const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
              const dayData = byDate.get(dateStr);
              const isToday = dateStr === today.toISOString().slice(0, 10);
              return (
                <div key={dateStr} className={cn("min-h-24 border-b border-r border-border p-1.5", isToday && "bg-primary/5")}>
                  <p className={cn("mb-1 text-xs font-medium", isToday ? "text-primary" : "text-muted-foreground")}>{day}</p>
                  <div className="space-y-1">
                    {(dayData?.items ?? []).slice(0, 3).map((item) => (
                      <Link
                        key={item.task_id}
                        to={`/compliance/tasks/${item.task_id}`}
                        className="block truncate rounded px-1 py-0.5 text-[11px] hover:underline"
                        title={item.title}
                      >
                        <Badge variant={item.is_overdue ? "destructive" : PRIORITY_VARIANT[item.priority]} className="mr-1 px-1 py-0 text-[10px]">
                          {item.is_overdue ? "OVERDUE" : item.status.replaceAll("_", " ")}
                        </Badge>
                        {item.title}
                      </Link>
                    ))}
                    {(dayData?.items.length ?? 0) > 3 && (
                      <p className="text-[10px] text-muted-foreground">+{(dayData?.items.length ?? 0) - 3} more</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
