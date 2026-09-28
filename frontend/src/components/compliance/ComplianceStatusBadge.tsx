import { Badge } from "@/components/ui/badge";
import type { ComplianceObligationStatus, ReadinessStatus } from "@/types/compliance";

interface ComplianceStatusBadgeProps {
  status: ComplianceObligationStatus;
  isOverdue?: boolean;
}

export function ComplianceStatusBadge({ status, isOverdue }: ComplianceStatusBadgeProps) {
  if (isOverdue || status === "OVERDUE") {
    return <Badge variant="destructive">OVERDUE</Badge>;
  }

  switch (status) {
    case "DRAFT":
      return <Badge variant="secondary">DRAFT</Badge>;
    case "ASSIGNED":
      return <Badge variant="outline" className="border-blue-500 text-blue-600 bg-blue-50 dark:bg-blue-950">ASSIGNED</Badge>;
    case "IN_PROGRESS":
      return <Badge variant="default" className="bg-amber-600 hover:bg-amber-700">IN PROGRESS</Badge>;
    case "READY_FOR_REVIEW":
    case "UNDER_REVIEW":
      return <Badge variant="warning">UNDER REVIEW</Badge>;
    case "APPROVED":
      return <Badge variant="outline" className="border-emerald-500 text-emerald-600 bg-emerald-50 dark:bg-emerald-950">APPROVED</Badge>;
    case "COMPLETED":
    case "FULFILLED":
      return <Badge variant="success">COMPLETED</Badge>;
    case "BLOCKED":
      return <Badge variant="destructive" className="bg-red-700">BLOCKED</Badge>;
    case "REJECTED":
      return <Badge variant="destructive">REJECTED</Badge>;
    case "REOPENED":
      return <Badge variant="warning">REOPENED</Badge>;
    case "CANCELLED":
      return <Badge variant="secondary" className="line-through">CANCELLED</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}

export function ReadinessBadge({ status }: { status: ReadinessStatus | string }) {
  switch (status) {
    case "READY":
      return <Badge variant="success">READY</Badge>;
    case "READY_WITH_WARNINGS":
      return <Badge variant="warning">READY (WARNINGS)</Badge>;
    case "BLOCKED":
      return <Badge variant="destructive">BLOCKED</Badge>;
    case "MISSING_DATA":
      return <Badge variant="destructive" className="bg-orange-600">MISSING DATA</Badge>;
    case "NOT_APPLICABLE":
    default:
      return <Badge variant="secondary">N/A</Badge>;
  }
}

export const ComplianceReadinessBadge = ReadinessBadge;

