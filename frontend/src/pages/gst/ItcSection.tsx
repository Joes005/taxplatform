import { useState } from "react";
import { CheckCircle2, ShieldQuestion, XCircle } from "lucide-react";

import { useToast } from "@/hooks/useToast";
import { useApproveItc, useItcResults, useItcSummary, useReviewItc } from "@/hooks/useItc";
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
import type { ITCCategory, ITCReviewStatus } from "@/types/gst";

const CATEGORIES: ITCCategory[] = ["MATCHED_ITC", "UNMATCHED_ITC", "POTENTIAL_ITC", "REVIEW_REQUIRED", "INELIGIBLE"];

const REVIEW_STATUS_VARIANT: Record<ITCReviewStatus, "secondary" | "warning" | "success" | "destructive"> = {
  PENDING: "secondary",
  REVIEWED: "warning",
  ACCEPTED: "success",
  REJECTED: "destructive",
};

export function ItcSection({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { toast } = useToast();
  const [category, setCategory] = useState<string>("");
  const { data: summary, isLoading: summaryLoading, isError } = useItcSummary(companyId, periodId);
  const { data: results, isLoading: resultsLoading } = useItcResults(companyId, periodId, category || undefined);
  const reviewMutation = useReviewItc(companyId, periodId);
  const approveMutation = useApproveItc(companyId, periodId);

  const handleReview = async (resultId: string) => {
    try {
      await reviewMutation.mutateAsync({ resultId });
      toast({ title: "Marked reviewed", variant: "success" });
    } catch (err) {
      toast({ title: "Could not update", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const handleApprove = async (resultId: string, approved: boolean) => {
    try {
      await approveMutation.mutateAsync({ resultId, approved });
      toast({ title: approved ? "ITC approved" : "ITC rejected", variant: "success" });
    } catch (err) {
      toast({ title: "Could not update", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Input Tax Credit derived from the latest reconciliation run. Only figures explicitly approved
        here feed into GSTR-3B's net liability.
      </p>

      {summaryLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : isError || !summary ? (
        <EmptyTableState icon={ShieldQuestion} title="No reconciliation run yet" hint="Run reconciliation first to see ITC." />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {CATEGORIES.map((cat) => {
            const entry = summary[cat];
            return (
              <Card key={cat}>
                <CardContent className="pt-6">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{cat.replaceAll("_", " ")}</p>
                  <p className="mt-1 text-lg font-semibold">{entry ? formatMoney(entry.total_itc) : formatMoney(0)}</p>
                  <p className="text-xs text-muted-foreground">{entry?.count ?? 0} records</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {summary && (
        <div className="space-y-3">
          <Select value={category || "__all__"} onValueChange={(v) => setCategory(v === "__all__" ? "" : v)}>
            <SelectTrigger className="w-56"><SelectValue placeholder="All categories" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All categories</SelectItem>
              {CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c.replaceAll("_", " ")}</SelectItem>)}
            </SelectContent>
          </Select>

          {resultsLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : results && results.items.length > 0 ? (
            <div className="rounded-lg border border-border bg-white">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Category</TableHead>
                    <TableHead className="text-right">CGST</TableHead>
                    <TableHead className="text-right">SGST</TableHead>
                    <TableHead className="text-right">IGST</TableHead>
                    <TableHead>Review Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.items.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="text-xs text-muted-foreground">{r.itc_category?.replaceAll("_", " ") ?? "—"}</TableCell>
                      <TableCell className="text-right">{formatMoney(r.books_cgst_amount)}</TableCell>
                      <TableCell className="text-right">{formatMoney(r.books_sgst_amount)}</TableCell>
                      <TableCell className="text-right">{formatMoney(r.books_igst_amount)}</TableCell>
                      <TableCell><Badge variant={REVIEW_STATUS_VARIANT[r.itc_review_status]}>{r.itc_review_status}</Badge></TableCell>
                      <TableCell className="text-right">
                        <PermissionGate permission="ITC_REVIEW">
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={r.itc_review_status !== "PENDING"}
                            onClick={() => handleReview(r.id)}
                          >
                            Mark reviewed
                          </Button>
                        </PermissionGate>
                        <PermissionGate permission="ITC_APPROVE">
                          <Button variant="ghost" size="sm" onClick={() => handleApprove(r.id, true)}>
                            <CheckCircle2 className="h-4 w-4 text-success" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleApprove(r.id, false)}>
                            <XCircle className="h-4 w-4 text-destructive" />
                          </Button>
                        </PermissionGate>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <EmptyTableState icon={ShieldQuestion} title="No ITC results for this filter" />
          )}
        </div>
      )}
    </div>
  );
}
