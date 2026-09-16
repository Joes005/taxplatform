import { useState } from "react";
import { GitCompare, PlayCircle } from "lucide-react";

import { useToast } from "@/hooks/useToast";
import { useLatestReconciliation, useReconciliationResults, useRunReconciliation } from "@/hooks/useReconciliation";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";
import { EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { ReconciliationStatus } from "@/types/gst";

const STATUS_OPTIONS: ReconciliationStatus[] = [
  "MATCHED", "PARTIALLY_MATCHED", "AMOUNT_MISMATCH", "DATE_MISMATCH", "GSTIN_MISMATCH",
  "INVOICE_NUMBER_MISMATCH", "BOOKS_ONLY", "GSTR2B_ONLY", "DUPLICATE", "REVIEW_REQUIRED",
];

const STATUS_VARIANT: Record<ReconciliationStatus, "success" | "warning" | "destructive" | "secondary"> = {
  MATCHED: "success",
  PARTIALLY_MATCHED: "warning",
  AMOUNT_MISMATCH: "destructive",
  DATE_MISMATCH: "destructive",
  GSTIN_MISMATCH: "destructive",
  INVOICE_NUMBER_MISMATCH: "destructive",
  BOOKS_ONLY: "secondary",
  GSTR2B_ONLY: "secondary",
  DUPLICATE: "warning",
  REVIEW_REQUIRED: "warning",
};

export function ReconciliationSection({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { toast } = useToast();
  const [status, setStatus] = useState<string>("");
  const { data: run, isLoading: runLoading, isError } = useLatestReconciliation(companyId, periodId);
  const { data: results, isLoading: resultsLoading } = useReconciliationResults(companyId, periodId, status || undefined);
  const runMutation = useRunReconciliation(companyId, periodId);

  const handleRun = async () => {
    try {
      await runMutation.mutateAsync();
      toast({ title: "Reconciliation complete", variant: "success" });
    } catch (err) {
      toast({ title: "Reconciliation failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">Compares posted purchase invoices against imported GSTR-2B records.</p>
        <PermissionGate permission="GSTR2B_RECONCILE">
          <Button size="sm" onClick={handleRun} disabled={runMutation.isPending}>
            <PlayCircle className="mr-1.5 h-4 w-4" />
            {runMutation.isPending ? "Running…" : run ? "Re-run reconciliation" : "Run reconciliation"}
          </Button>
        </PermissionGate>
      </div>

      {runLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : isError || !run ? (
        <EmptyTableState icon={GitCompare} title="No reconciliation run yet" hint="Run it to compare books against GSTR-2B." />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          {[
            ["Purchases", run.total_purchase_invoices],
            ["Matched", run.matched_count],
            ["Partial", run.partially_matched_count],
            ["Mismatch", run.mismatch_count],
            ["Books Only", run.books_only_count],
            ["2B Only", run.gstr2b_only_count],
            ["Match %", `${run.match_percentage}%`],
          ].map(([label, value]) => (
            <Card key={label as string}>
              <CardContent className="pt-6">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
                <p className="mt-1 text-lg font-semibold">{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {run && (
        <div className="space-y-3">
          <Select value={status || "__all__"} onValueChange={(v) => setStatus(v === "__all__" ? "" : v)}>
            <SelectTrigger className="w-56"><SelectValue placeholder="All statuses" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All statuses</SelectItem>
              {STATUS_OPTIONS.map((s) => <SelectItem key={s} value={s}>{s.replaceAll("_", " ")}</SelectItem>)}
            </SelectContent>
          </Select>

          {resultsLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : results && results.items.length > 0 ? (
            <div className="rounded-lg border border-border bg-white">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Books Taxable</TableHead>
                    <TableHead className="text-right">2B Taxable</TableHead>
                    <TableHead className="text-right">Taxable Diff</TableHead>
                    <TableHead className="text-right">Tax Diff</TableHead>
                    <TableHead>ITC Category</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.items.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell><Badge variant={STATUS_VARIANT[r.status]}>{r.status.replaceAll("_", " ")}</Badge></TableCell>
                      <TableCell className="text-right">{formatMoney(r.books_taxable_value)}</TableCell>
                      <TableCell className="text-right">{formatMoney(r.gstr2b_taxable_value)}</TableCell>
                      <TableCell className="text-right">{formatMoney(r.taxable_value_diff)}</TableCell>
                      <TableCell className="text-right">{formatMoney(r.tax_diff)}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{r.itc_category ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <EmptyTableState icon={GitCompare} title="No results for this filter" />
          )}
        </div>
      )}
    </div>
  );
}
