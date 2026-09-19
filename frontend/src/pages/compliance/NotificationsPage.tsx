import { Link } from "react-router-dom";
import { Bell } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useMarkAllNotificationsRead, useMarkNotificationRead, useNotifications } from "@/hooks/useNotifications";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { NotificationSeverity } from "@/types/compliance";

const SEVERITY_VARIANT: Record<NotificationSeverity, "secondary" | "warning" | "destructive"> = {
  INFO: "secondary",
  WARNING: "warning",
  CRITICAL: "destructive",
};

export default function NotificationsPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={Bell} />;
  const companyId = activeCompany.company_id;

  const { data, isLoading } = useNotifications(companyId);
  const markRead = useMarkNotificationRead(companyId);
  const markAllRead = useMarkAllNotificationsRead(companyId);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Notifications</h1>
          <p className="text-sm text-muted-foreground">In-app only — no email or SMS is ever sent.</p>
        </div>
        <Button size="sm" variant="outline" onClick={() => markAllRead.mutate()}>Mark all as read</Button>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="p-6"><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <div className="divide-y divide-border">
            {data.items.map((n) => (
              <div key={n.id} className={`flex items-start justify-between gap-3 p-4 ${n.is_read ? "" : "bg-primary/5"}`}>
                <div className="flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <Badge variant={SEVERITY_VARIANT[n.severity]}>{n.type.replaceAll("_", " ")}</Badge>
                    <span className="text-xs text-muted-foreground">{new Date(n.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-sm font-medium">{n.title}</p>
                  <p className="text-sm text-muted-foreground">{n.message}</p>
                  {n.entity_type === "compliance_task" && n.entity_id && (
                    <Link to={`/compliance/tasks/${n.entity_id}`} className="text-xs font-medium text-primary hover:underline">
                      Open task
                    </Link>
                  )}
                </div>
                {!n.is_read && (
                  <Button size="sm" variant="ghost" onClick={() => markRead.mutate(n.id)}>Mark read</Button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <EmptyTableState icon={Bell} title="No notifications yet" />
        )}
      </div>
    </div>
  );
}
