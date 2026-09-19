import { Link } from "react-router-dom";
import { Bell } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useMarkNotificationRead, useUnreadNotificationCount, useUnreadNotifications } from "@/hooks/useNotifications";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function NotificationBell() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;
  const { data: countData } = useUnreadNotificationCount(companyId);
  const { data: unread } = useUnreadNotifications(companyId);
  const markRead = useMarkNotificationRead(companyId ?? "");

  if (!companyId) return null;
  const count = countData?.unread_count ?? 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="relative flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent">
          <Bell className="h-4 w-4" />
          {count > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold text-white">
              {count > 9 ? "9+" : count}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {(unread?.items ?? []).length === 0 ? (
          <p className="px-2 py-3 text-center text-sm text-muted-foreground">You're all caught up.</p>
        ) : (
          (unread?.items ?? []).map((n) => (
            <DropdownMenuItem
              key={n.id}
              className="flex flex-col items-start gap-0.5 whitespace-normal"
              onClick={() => markRead.mutate(n.id)}
            >
              <div className="flex w-full items-center justify-between gap-2">
                <span className="text-xs font-medium">{n.title}</span>
                <Badge variant="secondary" className="text-[10px]">{n.type.replaceAll("_", " ")}</Badge>
              </div>
              <span className="text-xs text-muted-foreground">{n.message}</span>
            </DropdownMenuItem>
          ))
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/notifications" className="w-full text-center text-xs font-medium text-primary">
            View all notifications
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
