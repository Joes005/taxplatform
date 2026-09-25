import { Link } from "react-router-dom";
import { Landmark, Receipt, ScrollText } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useBankAccounts } from "@/hooks/useBankAccounts";
import { useBankReconciliations } from "@/hooks/useBankReconciliations";
import { useBankTransactions } from "@/hooks/useBankTransactions";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { BankReconciliationStatus } from "@/types/bank";

const RECON_STATUS_VARIANT: Record<BankReconciliationStatus, "secondary" | "warning" | "success" | "outline" | "destructive"> = {
  OPEN: "secondary",
  IN_PROGRESS: "warning",
  PENDING_REVIEW: "warning",
  RECONCILED: "success",
  LOCKED: "success",
  CANCELLED: "outline",
};

export default function BankDashboardPage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;

  const { data: accounts, isLoading: accountsLoading } = useBankAccounts(companyId);
  const { data: reconciliations, isLoading: reconLoading } = useBankReconciliations(companyId);
  const { data: unmatched } = useBankTransactions(companyId, 1, { reconciliationStatus: "UNMATCHED" });
  const { data: matched } = useBankTransactions(companyId, 1, { reconciliationStatus: "MATCHED" });
  const { data: reviewRequired } = useBankTransactions(companyId, 1, { reconciliationStatus: "REVIEW_REQUIRED" });

  if (!activeCompany) return <EmptyCompanyState icon={Landmark} />;

  const cards: [string, string | number][] = [
    ["Bank Accounts", accountsLoading ? "…" : accounts?.pagination.total ?? 0],
    ["Unmatched Transactions", unmatched?.pagination.total ?? 0],
    ["Matched Transactions", matched?.pagination.total ?? 0],
    ["Pending Review", reviewRequired?.pagination.total ?? 0],
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Bank Reconciliation</h1>
        <p className="text-sm text-muted-foreground">
          Import bank statements, match them against your books, and track reconciliation status — a local
          preparation workspace, never a live bank connection.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {cards.map(([label, value]) => (
          <Card key={label}>
            <CardContent className="pt-6">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className="mt-1 text-lg font-semibold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <ScrollText className="h-4 w-4" /> Reconciliation Sessions
            </h2>
            <Link to="/bank/reconciliations" className="text-xs font-medium text-primary hover:underline">
              View all
            </Link>
          </div>
          {reconLoading ? (
            <div className="p-6"><Skeleton className="h-10 w-full" /></div>
          ) : reconciliations && reconciliations.items.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Bank Balance</TableHead>
                  <TableHead className="text-right">Book Balance</TableHead>
                  <TableHead className="text-right">Difference</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reconciliations.items.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>
                      <Link to={`/bank/reconciliations/${r.id}`} className="font-medium text-primary hover:underline">
                        {r.period_start} to {r.period_end}
                      </Link>
                    </TableCell>
                    <TableCell className="text-right">{r.bank_balance ? formatMoney(r.bank_balance) : "—"}</TableCell>
                    <TableCell className="text-right">{r.book_balance ? formatMoney(r.book_balance) : "—"}</TableCell>
                    <TableCell className="text-right">{r.difference ? formatMoney(r.difference) : "—"}</TableCell>
                    <TableCell><Badge variant={RECON_STATUS_VARIANT[r.status]}>{r.status}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyTableState icon={Receipt} title="No reconciliation sessions yet" hint="Start one from a bank account." />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
