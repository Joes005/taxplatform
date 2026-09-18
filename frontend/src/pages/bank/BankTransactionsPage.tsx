import { useState } from "react";
import { EyeOff, Flag, Receipt } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useBankAccounts } from "@/hooks/useBankAccounts";
import { useBankTransactions, useExcludeBankTransaction, useFlagBankTransactionForReview } from "@/hooks/useBankTransactions";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError } from "@/lib/api-client";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { BankTransactionReconciliationStatus } from "@/types/bank";

const STATUS_VARIANT: Record<BankTransactionReconciliationStatus, "secondary" | "warning" | "success" | "outline" | "destructive"> = {
  UNMATCHED: "secondary",
  MATCH_SUGGESTED: "warning",
  PARTIALLY_MATCHED: "warning",
  MATCHED: "success",
  MANUALLY_MATCHED: "success",
  EXCLUDED: "outline",
  REVIEW_REQUIRED: "destructive",
};

const statuses: BankTransactionReconciliationStatus[] = [
  "UNMATCHED", "MATCH_SUGGESTED", "PARTIALLY_MATCHED", "MATCHED", "MANUALLY_MATCHED", "EXCLUDED", "REVIEW_REQUIRED",
];

export default function BankTransactionsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";

  const [bankAccountId, setBankAccountId] = useState<string>("");
  const [status, setStatus] = useState<BankTransactionReconciliationStatus | "">("");
  const [search, setSearch] = useState("");

  const { data: accounts } = useBankAccounts(companyId);
  const { data, isLoading } = useBankTransactions(companyId, 1, {
    bankAccountId: bankAccountId || undefined,
    reconciliationStatus: (status || undefined) as BankTransactionReconciliationStatus | undefined,
    search: search || undefined,
  });
  const excludeMutation = useExcludeBankTransaction(companyId);
  const reviewMutation = useFlagBankTransactionForReview(companyId);

  if (!activeCompany) return <EmptyCompanyState icon={Receipt} />;

  const runAction = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast({ title: message, variant: "success" });
    } catch (err) {
      toast({ title: "Action failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Bank Transactions</h1>
        <p className="text-sm text-muted-foreground">All imported transactions across your bank accounts.</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Select value={bankAccountId || "__all__"} onValueChange={(v) => setBankAccountId(v === "__all__" ? "" : v)}>
          <SelectTrigger className="w-56"><SelectValue placeholder="All accounts" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All accounts</SelectItem>
            {(accounts?.items ?? []).map((a) => <SelectItem key={a.id} value={a.id}>{a.account_name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={status || "__all__"} onValueChange={(v) => setStatus(v === "__all__" ? "" : (v as BankTransactionReconciliationStatus))}>
          <SelectTrigger className="w-56"><SelectValue placeholder="All statuses" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All statuses</SelectItem>
            {statuses.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
        <Input placeholder="Search description/reference…" className="w-64" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Reference</TableHead>
                <TableHead className="text-right">Debit</TableHead>
                <TableHead className="text-right">Credit</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((t) => (
                <TableRow key={t.id}>
                  <TableCell className="text-muted-foreground">{t.transaction_date}</TableCell>
                  <TableCell className="max-w-xs truncate" title={t.description}>{t.description}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{t.reference_number ?? "—"}</TableCell>
                  <TableCell className="text-right">{Number(t.debit_amount) > 0 ? formatMoney(t.debit_amount) : "—"}</TableCell>
                  <TableCell className="text-right">{Number(t.credit_amount) > 0 ? formatMoney(t.credit_amount) : "—"}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[t.reconciliation_status]}>{t.reconciliation_status}</Badge></TableCell>
                  <TableCell className="text-right">
                    {(t.reconciliation_status === "UNMATCHED" || t.reconciliation_status === "MATCH_SUGGESTED" || t.reconciliation_status === "REVIEW_REQUIRED") && (
                      <div className="flex justify-end gap-1.5">
                        <PermissionGate permission="BANK_TRANSACTION_UPDATE">
                          <Button size="sm" variant="ghost" onClick={() => runAction(() => reviewMutation.mutateAsync(t.id), "Flagged for review")}>
                            <Flag className="mr-1 h-3.5 w-3.5" /> Review
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => runAction(() => excludeMutation.mutateAsync(t.id), "Excluded")}>
                            <EyeOff className="mr-1 h-3.5 w-3.5" /> Exclude
                          </Button>
                        </PermissionGate>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Receipt} title="No transactions found" hint="Import a bank statement to see transactions here." />
        )}
      </div>
    </div>
  );
}
