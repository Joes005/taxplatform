import { Link } from "react-router-dom";
import { ClipboardCheck, ScrollText } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useAuditDashboard } from "@/hooks/useAuditReports";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { AuditEngagementStatus } from "@/types/audit";

const STATUS_VARIANT: Record<AuditEngagementStatus, "secondary" | "warning" | "success" | "outline"> = {
  DRAFT: "outline",
  OPEN: "secondary",
  ASSIGNED: "secondary",
  IN_REVIEW: "warning",
  PENDING_CLIENT_ACTION: "warning",
  PENDING_AUDITOR_REVIEW: "warning",
  APPROVED: "success",
  SIGNED_OFF: "success",
  CLOSED: "success",
  CANCELLED: "outline",
};

export default function AuditDashboardPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={ClipboardCheck} />;
  const companyId = activeCompany.company_id;

  const { data, isLoading } = useAuditDashboard(companyId);

  const engagementCards: [string, number][] = data
    ? [
        ["Draft", data.engagements_by_status.DRAFT ?? 0],
        ["In Review", (data.engagements_by_status.IN_REVIEW ?? 0) + (data.engagements_by_status.ASSIGNED ?? 0)],
        ["Pending Auditor Review", data.engagements_by_status.PENDING_AUDITOR_REVIEW ?? 0],
        ["Closed", data.engagements_by_status.CLOSED ?? 0],
      ]
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Audit Workflow</h1>
        <p className="text-sm text-muted-foreground">
          Engagements, findings, and review sign-off for a CA/auditor working inside this company's data — an
          internal workflow tool, never a statutory audit or legal opinion.
        </p>
      </div>

      {isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {engagementCards.map(([label, value]) => (
            <Card key={label}>
              <CardContent className="pt-6">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
                <p className="mt-1 text-lg font-semibold">{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <ScrollText className="h-4 w-4" /> Review Queue
            </h2>
            <Link to="/audits/engagements" className="text-xs font-medium text-primary hover:underline">
              View all engagements
            </Link>
          </div>
          {isLoading ? (
            <div className="p-6"><Skeleton className="h-10 w-full" /></div>
          ) : data && data.review_queue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Engagement</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Open Findings</TableHead>
                  <TableHead className="text-right">High/Critical</TableHead>
                  <TableHead className="text-right">Pending Responses</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.review_queue.map((item) => (
                  <TableRow key={item.engagement.id}>
                    <TableCell>
                      <Link to={`/audits/engagements/${item.engagement.id}`} className="font-medium text-primary hover:underline">
                        {item.engagement.engagement_code} — {item.engagement.title}
                      </Link>
                    </TableCell>
                    <TableCell><Badge variant={STATUS_VARIANT[item.engagement.status]}>{item.engagement.status}</Badge></TableCell>
                    <TableCell className="text-right">{item.open_findings}</TableCell>
                    <TableCell className="text-right">{item.high_or_critical_open_findings}</TableCell>
                    <TableCell className="text-right">{item.pending_responses}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyTableState icon={ScrollText} title="Nothing waiting on auditor review" hint="Engagements appear here once they're submitted for auditor review." />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
