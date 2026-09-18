import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Landmark, MessageSquarePlus } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useTdsReturnPeriod } from "@/hooks/useTdsReturnPeriods";
import {
  useApproveTdsReturn,
  useFinalizeTdsReturn,
  useGenerateTdsReturnSnapshot,
  useLatestTdsReturnSnapshot,
  useRequestTdsReturnChanges,
  useSubmitTdsReturnForReview,
} from "@/hooks/useTdsReturnSnapshots";
import {
  useTdsChallanReportSummary,
  useTdsDeducteeSummary,
  useTdsQuarterlySummary,
  useTdsSectionSummary,
} from "@/hooks/useTdsReports";
import { useTdsReconciliation, useRunTdsReconciliation } from "@/hooks/useTdsReconciliation";
import { useCreateTdsReviewNote, useResolveTdsReviewNote, useTdsReviewNotes } from "@/hooks/useTdsReviewNotes";
import { tdsReportService } from "@/services/tdsReportService";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api-client";
import { formatMoney, triggerBlobDownload } from "@/lib/utils";
import { EmptyCompanyState } from "@/pages/accounting/LedgersPage";
import type { TDSReturnPeriodStatus, TDSReturnSnapshotStatus } from "@/types/tds";

const PERIOD_STATUS_VARIANT: Record<TDSReturnPeriodStatus, "secondary" | "warning" | "success" | "outline"> = {
  OPEN: "secondary",
  UNDER_REVIEW: "warning",
  APPROVED: "warning",
  FINALIZED: "success",
  ARCHIVED: "outline",
};

const SNAPSHOT_STATUS_VARIANT: Record<TDSReturnSnapshotStatus, "secondary" | "warning" | "success" | "destructive"> = {
  DRAFT: "secondary",
  UNDER_REVIEW: "warning",
  CHANGES_REQUESTED: "destructive",
  APPROVED: "warning",
  FINALIZED: "success",
};

export default function TdsReturnPeriodDetailPage() {
  const { periodId } = useParams<{ periodId: string }>();
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={Landmark} />;

  const companyId = activeCompany.company_id;
  const { data: period, isLoading } = useTdsReturnPeriod(companyId, periodId);

  if (isLoading || !period || !periodId) {
    return <Skeleton className="h-64 w-full" />;
  }

  return (
    <div className="space-y-6">
      <Link to="/tds" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to TDS
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{period.quarter} {period.period_start.slice(0, 4)}</h1>
          <p className="text-sm text-muted-foreground">{period.period_start} to {period.period_end}</p>
        </div>
        <Badge variant={PERIOD_STATUS_VARIANT[period.status]} className="text-sm">{period.status}</Badge>
      </div>

      <WorkflowBar companyId={companyId} periodId={periodId} />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="sections">By Section</TabsTrigger>
          <TabsTrigger value="deductees">By Deductee</TabsTrigger>
          <TabsTrigger value="challans">Challans</TabsTrigger>
          <TabsTrigger value="reconciliation">Reconciliation</TabsTrigger>
          <TabsTrigger value="review">Review Notes</TabsTrigger>
        </TabsList>

        <TabsContent value="overview"><OverviewTab companyId={companyId} periodId={periodId} /></TabsContent>
        <TabsContent value="sections"><SectionsTab companyId={companyId} periodId={periodId} /></TabsContent>
        <TabsContent value="deductees"><DeducteesTab companyId={companyId} periodId={periodId} /></TabsContent>
        <TabsContent value="challans"><ChallansTab companyId={companyId} periodId={periodId} /></TabsContent>
        <TabsContent value="reconciliation">
          <ReconciliationTab companyId={companyId} financialYearId={period.financial_year_id} />
        </TabsContent>
        <TabsContent value="review"><ReviewNotesTab companyId={companyId} periodId={periodId} /></TabsContent>
      </Tabs>
    </div>
  );
}

function WorkflowBar({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { toast } = useToast();
  const { data: snapshot } = useLatestTdsReturnSnapshot(companyId, periodId);
  const generateMutation = useGenerateTdsReturnSnapshot(companyId, periodId);
  const submitMutation = useSubmitTdsReturnForReview(companyId, periodId);
  const approveMutation = useApproveTdsReturn(companyId, periodId);
  const requestChangesMutation = useRequestTdsReturnChanges(companyId, periodId);
  const finalizeMutation = useFinalizeTdsReturn(companyId, periodId);
  const [downloading, setDownloading] = useState(false);

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast({ title: message, variant: "success" });
    } catch (err) {
      toast({ title: "Action failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const download = async (format: "csv" | "xlsx") => {
    setDownloading(true);
    try {
      const { blob, filename } = await tdsReportService.exportQuarterly(companyId, periodId, format);
      triggerBlobDownload(blob, filename ?? `tds-quarterly.${format}`);
    } catch (err) {
      toast({ title: "Export failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Return preparation:</span>
          {snapshot ? (
            <>
              <Badge variant={SNAPSHOT_STATUS_VARIANT[snapshot.status]}>v{snapshot.version} — {snapshot.status}</Badge>
            </>
          ) : (
            <span className="text-sm text-muted-foreground">Not generated yet</span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <PermissionGate permission="TDS_RETURN_GENERATE">
            <Button size="sm" variant="outline" onClick={() => run(() => generateMutation.mutateAsync(), "Return preparation generated")}>
              {snapshot ? "Regenerate" : "Generate"}
            </Button>
          </PermissionGate>
          {snapshot?.status === "DRAFT" && (
            <PermissionGate permission="TDS_RETURN_VALIDATE">
              <Button size="sm" variant="outline" onClick={() => run(() => submitMutation.mutateAsync(), "Submitted for review")}>
                Submit for review
              </Button>
            </PermissionGate>
          )}
          {snapshot?.status === "UNDER_REVIEW" && (
            <PermissionGate permission="TDS_RETURN_APPROVE">
              <Button size="sm" variant="outline" onClick={() => run(() => requestChangesMutation.mutateAsync(), "Changes requested")}>
                Request changes
              </Button>
              <Button size="sm" onClick={() => run(() => approveMutation.mutateAsync(), "Approved")}>
                Approve
              </Button>
            </PermissionGate>
          )}
          {snapshot?.status === "APPROVED" && (
            <PermissionGate permission="TDS_RETURN_FINALIZE">
              <Button size="sm" onClick={() => run(() => finalizeMutation.mutateAsync(), "Finalized")}>
                Finalize
              </Button>
            </PermissionGate>
          )}
          <PermissionGate permission="TDS_REPORT_EXPORT">
            <Button size="sm" variant="outline" disabled={downloading} onClick={() => download("csv")}>
              <Download className="mr-1.5 h-3.5 w-3.5" /> CSV
            </Button>
            <Button size="sm" variant="outline" disabled={downloading} onClick={() => download("xlsx")}>
              <Download className="mr-1.5 h-3.5 w-3.5" /> XLSX
            </Button>
          </PermissionGate>
        </div>
      </CardContent>
    </Card>
  );
}

function OverviewTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useTdsQuarterlySummary(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data) return null;

  const cards: [string, string | number][] = [
    ["Transactions", data.transaction_count],
    ["Deductees", data.deductee_count],
    ["Gross Amount", formatMoney(data.gross_amount)],
    ["TDS Deducted", formatMoney(data.tds_deducted)],
    ["TDS Paid", formatMoney(data.tds_paid)],
    ["TDS Outstanding", formatMoney(data.tds_outstanding)],
    ["Pending Review", data.review_required_count],
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {cards.map(([label, value]) => (
        <Card key={label}>
          <CardContent className="pt-6">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
            <p className="mt-1 text-lg font-semibold">{value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function SectionsTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useTdsSectionSummary(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.length === 0) return <p className="text-sm text-muted-foreground">No transactions this quarter.</p>;

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Section</TableHead>
          <TableHead className="text-right">Transactions</TableHead>
          <TableHead className="text-right">Gross</TableHead>
          <TableHead className="text-right">TDS Deducted</TableHead>
          <TableHead className="text-right">TDS Paid</TableHead>
          <TableHead className="text-right">Outstanding</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.tds_section_id}>
            <TableCell className="font-medium">{row.section_code}</TableCell>
            <TableCell className="text-right">{row.transaction_count}</TableCell>
            <TableCell className="text-right">{formatMoney(row.gross_amount)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.tds_deducted)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.tds_paid)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.tds_outstanding)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function DeducteesTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useTdsDeducteeSummary(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.length === 0) return <p className="text-sm text-muted-foreground">No transactions this quarter.</p>;

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Deductee</TableHead>
          <TableHead>PAN</TableHead>
          <TableHead className="text-right">Transactions</TableHead>
          <TableHead className="text-right">Gross</TableHead>
          <TableHead className="text-right">TDS Deducted</TableHead>
          <TableHead className="text-right">TDS Paid</TableHead>
          <TableHead className="text-right">Outstanding</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.deductee_id}>
            <TableCell className="font-medium">{row.deductee_name}</TableCell>
            <TableCell className="font-mono text-xs text-muted-foreground">{row.pan ?? "—"}</TableCell>
            <TableCell className="text-right">{row.transaction_count}</TableCell>
            <TableCell className="text-right">{formatMoney(row.gross_amount)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.tds_deducted)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.tds_paid)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.tds_outstanding)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ChallansTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useTdsChallanReportSummary(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.length === 0) return <p className="text-sm text-muted-foreground">No challans recorded for this financial year yet.</p>;

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Challan #</TableHead>
          <TableHead className="text-right">Amount</TableHead>
          <TableHead className="text-right">Allocated</TableHead>
          <TableHead className="text-right">Unallocated</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.challan_id}>
            <TableCell className="font-medium">{row.challan_number}</TableCell>
            <TableCell className="text-right">{formatMoney(row.amount)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.allocated_amount)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.unallocated_amount)}</TableCell>
            <TableCell><Badge variant="outline">{row.status}</Badge></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ReconciliationTab({ companyId, financialYearId }: { companyId: string; financialYearId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useTdsReconciliation(companyId, financialYearId);
  const runMutation = useRunTdsReconciliation(companyId);

  const run = async () => {
    try {
      await runMutation.mutateAsync(financialYearId);
      toast({ title: "Reconciliation complete", variant: "success" });
    } catch (err) {
      toast({ title: "Reconciliation failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <PermissionGate permission="TDS_CHALLAN_RECONCILE">
          <Button size="sm" onClick={run} disabled={runMutation.isPending}>
            {runMutation.isPending ? "Running…" : "Run reconciliation"}
          </Button>
        </PermissionGate>
      </div>
      {isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : data && data.items.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Status</TableHead>
              <TableHead>Transaction</TableHead>
              <TableHead>Challan</TableHead>
              <TableHead className="text-right">Expected</TableHead>
              <TableHead className="text-right">Allocated</TableHead>
              <TableHead className="text-right">Variance</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((row) => (
              <TableRow key={row.id}>
                <TableCell><Badge variant={row.status === "MATCHED" ? "success" : "warning"}>{row.status}</Badge></TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">{row.tds_transaction_id?.slice(0, 8) ?? "—"}</TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">{row.tds_challan_id?.slice(0, 8) ?? "—"}</TableCell>
                <TableCell className="text-right">{row.expected_amount ? formatMoney(row.expected_amount) : "—"}</TableCell>
                <TableCell className="text-right">{row.allocated_amount ? formatMoney(row.allocated_amount) : "—"}</TableCell>
                <TableCell className="text-right">{row.variance_amount ? formatMoney(row.variance_amount) : "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <p className="text-sm text-muted-foreground">No reconciliation findings yet — run reconciliation to compare deductions against challans.</p>
      )}
    </div>
  );
}

function ReviewNotesTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useTdsReviewNotes(companyId, periodId);
  const createMutation = useCreateTdsReviewNote(companyId, periodId);
  const resolveMutation = useResolveTdsReviewNote(companyId, periodId);
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");

  const submit = async () => {
    if (!note.trim()) return;
    try {
      await createMutation.mutateAsync({
        return_period_id: periodId,
        entity_type: "TDS_RETURN_PERIOD",
        entity_id: periodId,
        note,
      });
      toast({ title: "Review note added", variant: "success" });
      setOpen(false);
      setNote("");
    } catch (err) {
      toast({ title: "Could not add note", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const resolve = async (noteId: string) => {
    try {
      await resolveMutation.mutateAsync(noteId);
      toast({ title: "Review note resolved", variant: "success" });
    } catch (err) {
      toast({ title: "Could not resolve note", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
          <MessageSquarePlus className="mr-1.5 h-3.5 w-3.5" /> Add note
        </Button>
      </div>
      {isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : data && data.length > 0 ? (
        <div className="space-y-2">
          {data.map((n) => (
            <Card key={n.id}>
              <CardContent className="flex items-start justify-between gap-4 pt-6">
                <div>
                  <p className="text-sm">{n.note}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{new Date(n.created_at).toLocaleString()}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge variant={n.status === "OPEN" ? "warning" : "success"}>{n.status}</Badge>
                  {n.status === "OPEN" && (
                    <Button size="sm" variant="ghost" onClick={() => resolve(n.id)}>Resolve</Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No review notes yet.</p>
      )}

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setNote(""); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add review note</DialogTitle>
            <DialogDescription>Visible to anyone reviewing this return period.</DialogDescription>
          </DialogHeader>
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4} placeholder="e.g. Verify deductee PAN before filing" />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="button" onClick={submit} disabled={createMutation.isPending}>
              {createMutation.isPending ? "Adding…" : "Add note"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
