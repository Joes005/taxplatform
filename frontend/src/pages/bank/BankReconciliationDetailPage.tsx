import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Landmark } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useBankReconciliation, useBankReconciliationSummary } from "@/hooks/useBankReconciliations";
import {
  useApproveBankReconciliation,
  useCancelBankReconciliation,
  useLockBankReconciliation,
  useRejectBankReconciliation,
  useRunBankMatching,
  useSubmitBankReconciliation,
} from "@/hooks/useBankReconciliations";
import { useBankMatchCandidates, useCreateBankMatch } from "@/hooks/useBankMatches";
import { useBankTransactions } from "@/hooks/useBankTransactions";
import { bankReportService } from "@/services/bankReportService";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError } from "@/lib/api-client";
import { formatMoney, triggerBlobDownload } from "@/lib/utils";
import { EmptyCompanyState } from "@/pages/accounting/LedgersPage";
import type { BankMatchSourceType, BankReconciliationStatus, BankTransaction } from "@/types/bank";

const STATUS_VARIANT: Record<BankReconciliationStatus, "secondary" | "warning" | "success" | "outline"> = {
  OPEN: "secondary",
  IN_PROGRESS: "warning",
  PENDING_REVIEW: "warning",
  RECONCILED: "success",
  LOCKED: "success",
  CANCELLED: "outline",
};

export default function BankReconciliationDetailPage() {
  const { reconciliationId } = useParams<{ reconciliationId: string }>();
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id;

  const { data: reconciliation, isLoading } = useBankReconciliation(companyId, reconciliationId);
  const { data: summary } = useBankReconciliationSummary(companyId, reconciliationId);

  const runMatching = useRunBankMatching(companyId ?? "", reconciliationId ?? "");
  const submit = useSubmitBankReconciliation(companyId ?? "", reconciliationId ?? "");
  const approve = useApproveBankReconciliation(companyId ?? "", reconciliationId ?? "");
  const reject = useRejectBankReconciliation(companyId ?? "", reconciliationId ?? "");
  const lock = useLockBankReconciliation(companyId ?? "", reconciliationId ?? "");
  const cancel = useCancelBankReconciliation(companyId ?? "", reconciliationId ?? "");

  const { data: openTransactions, isLoading: txnsLoading } = useBankTransactions(companyId, 1, {
    bankAccountId: reconciliation?.bank_account_id,
  });

  const [matchTarget, setMatchTarget] = useState<BankTransaction | null>(null);
  const [downloading, setDownloading] = useState(false);

  if (!activeCompany || !companyId) return <EmptyCompanyState icon={Landmark} />;
  if (isLoading || !reconciliation || !reconciliationId) return <Skeleton className="h-64 w-full" />;

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
      const { blob, filename } = await bankReportService.exportReconciliation(companyId, reconciliationId, format);
      triggerBlobDownload(blob, filename ?? `bank-reconciliation.${format}`);
    } catch (err) {
      toast({ title: "Export failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  };

  const openItems = (openTransactions?.items ?? []).filter((t) =>
    ["UNMATCHED", "MATCH_SUGGESTED", "REVIEW_REQUIRED", "PARTIALLY_MATCHED"].includes(t.reconciliation_status)
  );

  return (
    <div className="space-y-6">
      <Link to="/bank/reconciliations" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to reconciliations
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{reconciliation.period_start} to {reconciliation.period_end}</h1>
          <p className="text-sm text-muted-foreground">Bank reconciliation session</p>
        </div>
        <Badge variant={STATUS_VARIANT[reconciliation.status]} className="text-sm">{reconciliation.status}</Badge>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
          <div className="flex gap-6 text-sm">
            <div><p className="text-xs text-muted-foreground">Bank Balance</p><p className="font-semibold">{reconciliation.bank_balance ? formatMoney(reconciliation.bank_balance) : "—"}</p></div>
            <div><p className="text-xs text-muted-foreground">Book Balance</p><p className="font-semibold">{reconciliation.book_balance ? formatMoney(reconciliation.book_balance) : "—"}</p></div>
            <div><p className="text-xs text-muted-foreground">Difference</p><p className="font-semibold">{reconciliation.difference ? formatMoney(reconciliation.difference) : "—"}</p></div>
          </div>
          <div className="flex flex-wrap gap-2">
            {(reconciliation.status === "OPEN" || reconciliation.status === "IN_PROGRESS") && (
              <PermissionGate permission="BANK_RECONCILE_RUN">
                <Button size="sm" variant="outline" onClick={() => run(() => runMatching.mutateAsync(), "Matching run complete")}>
                  Run matching
                </Button>
              </PermissionGate>
            )}
            {reconciliation.status === "IN_PROGRESS" && (
              <PermissionGate permission="BANK_RECONCILE_SUBMIT">
                <Button size="sm" onClick={() => run(() => submit.mutateAsync(), "Submitted for review")}>Submit for review</Button>
              </PermissionGate>
            )}
            {reconciliation.status === "PENDING_REVIEW" && (
              <PermissionGate permission="BANK_RECONCILE_APPROVE">
                <Button size="sm" variant="outline" onClick={() => run(() => reject.mutateAsync(), "Returned for correction")}>Reject</Button>
                <Button size="sm" onClick={() => run(() => approve.mutateAsync(), "Approved")}>Approve</Button>
              </PermissionGate>
            )}
            {reconciliation.status === "RECONCILED" && (
              <PermissionGate permission="BANK_RECONCILE_LOCK">
                <Button size="sm" onClick={() => run(() => lock.mutateAsync(), "Locked")}>Lock</Button>
              </PermissionGate>
            )}
            {(reconciliation.status === "OPEN" || reconciliation.status === "IN_PROGRESS") && (
              <PermissionGate permission="BANK_RECONCILE_RUN">
                <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => run(() => cancel.mutateAsync(), "Cancelled")}>
                  Cancel
                </Button>
              </PermissionGate>
            )}
            <PermissionGate permission="BANK_REPORT_EXPORT">
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

      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {([
            ["Matched", summary.matched_count],
            ["Partially Matched", summary.partially_matched_count],
            ["Unmatched", summary.unmatched_count],
            ["Review Required", summary.review_required_count],
            ["Excluded", summary.excluded_count],
          ] as [string, number][]).map(([label, value]) => (
            <Card key={label}>
              <CardContent className="pt-6">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
                <p className="mt-1 text-lg font-semibold">{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Open Bank Transactions
        </h2>
        <div className="rounded-lg border border-border bg-white">
          {txnsLoading ? (
            <div className="p-6"><Skeleton className="h-10 w-full" /></div>
          ) : openItems.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {openItems.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="text-muted-foreground">{t.transaction_date}</TableCell>
                    <TableCell className="max-w-xs truncate" title={t.description}>{t.description}</TableCell>
                    <TableCell className="text-right">{formatMoney(t.amount)}</TableCell>
                    <TableCell><Badge variant="warning">{t.reconciliation_status}</Badge></TableCell>
                    <TableCell className="text-right">
                      <PermissionGate permission="BANK_MATCH_CREATE">
                        <Button size="sm" variant="outline" onClick={() => setMatchTarget(t)}>Match</Button>
                      </PermissionGate>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="p-6 text-sm text-muted-foreground">No open transactions — everything is matched or excluded.</p>
          )}
        </div>
      </div>

      <MatchDialog
        companyId={companyId}
        transaction={matchTarget}
        onClose={() => setMatchTarget(null)}
      />
    </div>
  );
}

function MatchDialog({
  companyId,
  transaction,
  onClose,
}: {
  companyId: string;
  transaction: BankTransaction | null;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const { data: candidates, isLoading } = useBankMatchCandidates(companyId, transaction?.id);
  const createMatch = useCreateBankMatch(companyId, transaction?.id ?? "");
  const [amount, setAmount] = useState("");

  const confirmMatch = async (sourceType: BankMatchSourceType, sourceId: string, defaultAmount: string) => {
    try {
      await createMatch.mutateAsync({
        source_type: sourceType,
        source_id: sourceId,
        matched_amount: amount || defaultAmount,
      });
      toast({ title: "Match created", variant: "success" });
      onClose();
    } catch (err) {
      toast({ title: "Match failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <Dialog open={!!transaction} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Match transaction</DialogTitle>
          <DialogDescription>
            {transaction && (
              <>
                {transaction.transaction_date} — {transaction.description} — {formatMoney(transaction.amount)}
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <Label htmlFor="match-amount">Amount to match (defaults to full amount)</Label>
          <Input
            id="match-amount"
            type="number"
            step="0.01"
            placeholder={transaction?.amount}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>

        {isLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : candidates && candidates.length > 0 ? (
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {candidates.map((c) => (
              <div key={`${c.source_type}-${c.source_id}`} className="flex items-center justify-between rounded-md border border-border p-3">
                <div>
                  <p className="text-sm font-medium">{c.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {c.source_date} · {formatMoney(c.source_amount)} {c.counterparty_name ? `· ${c.counterparty_name}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={c.confidence === "STRONG_MATCH" ? "success" : c.confidence === "MATCH_SUGGESTED" ? "warning" : "secondary"}>
                    {c.score} · {c.confidence}
                  </Badge>
                  <Button size="sm" onClick={() => confirmMatch(c.source_type, c.source_id, c.source_amount)} disabled={createMatch.isPending}>
                    Select
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            No automatic candidates found within a ±10 day, exact-amount window. Use manual matching from the
            accounting record's own page, or check the amount/date.
          </p>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
