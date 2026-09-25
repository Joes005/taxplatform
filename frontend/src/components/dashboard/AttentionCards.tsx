import { useNavigate } from "react-router-dom";
import { AlertCircle, AlertTriangle, Clock, Eye, AlertOctagon, CheckCircle2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { AttentionSummary } from "@/types/dashboard";

interface AttentionCardsProps {
  attention?: AttentionSummary;
  isLoading: boolean;
}

export function AttentionCards({ attention, isLoading }: AttentionCardsProps) {
  const navigate = useNavigate();

  const cards = [
    {
      label: "Critical",
      count: attention?.critical_count ?? 0,
      icon: AlertOctagon,
      bgColor: "bg-red-500/10",
      textColor: "text-red-600 dark:text-red-400",
      borderColor: "hover:border-red-500/50",
      onClick: () => navigate("/action-center?severity=CRITICAL"),
      description: "Immediate action required",
    },
    {
      label: "High Priority",
      count: attention?.high_priority_count ?? 0,
      icon: AlertCircle,
      bgColor: "bg-orange-500/10",
      textColor: "text-orange-600 dark:text-orange-400",
      borderColor: "hover:border-orange-500/50",
      onClick: () => navigate("/action-center?severity=HIGH"),
      description: "Urgent business tasks",
    },
    {
      label: "Due Soon",
      count: attention?.due_soon_count ?? 0,
      icon: Clock,
      bgColor: "bg-amber-500/10",
      textColor: "text-amber-600 dark:text-amber-400",
      borderColor: "hover:border-amber-500/50",
      onClick: () => navigate("/action-center?category=DUE_SOON"),
      description: "Deadlines in next 7 days",
    },
    {
      label: "Pending Review",
      count: attention?.pending_review_count ?? 0,
      icon: Eye,
      bgColor: "bg-blue-500/10",
      textColor: "text-blue-600 dark:text-blue-400",
      borderColor: "hover:border-blue-500/50",
      onClick: () => navigate("/action-center?category=REVIEW_REQUIRED"),
      description: "Awaiting sign-off or check",
    },
    {
      label: "Overdue",
      count: attention?.overdue_count ?? 0,
      icon: AlertTriangle,
      bgColor: "bg-rose-500/10",
      textColor: "text-rose-600 dark:text-rose-400",
      borderColor: "hover:border-rose-500/50",
      onClick: () => navigate("/action-center?category=OVERDUE"),
      description: "Past filing or due date",
    },
    {
      label: "Completed",
      count: attention?.completed_count ?? 0,
      icon: CheckCircle2,
      bgColor: "bg-emerald-500/10",
      textColor: "text-emerald-600 dark:text-emerald-400",
      borderColor: "hover:border-emerald-500/50",
      onClick: () => navigate("/action-center?status=RESOLVED"),
      description: "Resolved workflow items",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <Card
            key={card.label}
            onClick={card.onClick}
            className={`cursor-pointer transition-all hover:shadow-sm ${card.borderColor}`}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${card.bgColor}`}>
                  <Icon className={`h-4 w-4 ${card.textColor}`} />
                </div>
                {isLoading ? (
                  <Skeleton className="h-6 w-8" />
                ) : (
                  <span className={`text-xl font-bold ${card.textColor}`}>
                    {card.count}
                  </span>
                )}
              </div>
              <div className="mt-2">
                <p className="text-xs font-semibold text-foreground">{card.label}</p>
                <p className="text-[10px] text-muted-foreground truncate">{card.description}</p>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
