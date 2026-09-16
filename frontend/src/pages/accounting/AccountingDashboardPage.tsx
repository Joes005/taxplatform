import { useMemo } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowDownCircle, ArrowUpCircle, LayoutDashboard, UploadCloud, Wallet } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useCustomerOutstanding, useSalesSummary, usePurchaseSummary, useTrialBalance, useVendorOutstanding } from "@/hooks/useReports";
import { useImportJobs } from "@/hooks/useImports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState } from "./LedgersPage";

const PENDING_STATUSES = new Set(["UPLOADED", "PARSING", "VALIDATING", "READY", "PROCESSING"]);

function currentMonthRange() {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), 1);
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return { from: fmt(from), to: fmt(to) };
}

export default function AccountingDashboardPage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;
  const { from, to } = useMemo(currentMonthRange, []);

  const { data: sales, isLoading: salesLoading } = useSalesSummary(companyId, from, to);
  const { data: purchases, isLoading: purchasesLoading } = usePurchaseSummary(companyId, from, to);
  const { data: receivables, isLoading: receivablesLoading } = useCustomerOutstanding(companyId);
  const { data: payables, isLoading: payablesLoading } = useVendorOutstanding(companyId);
  const { data: trialBalance, isLoading: trialBalanceLoading } = useTrialBalance(companyId);
  const { data: imports, isLoading: importsLoading } = useImportJobs(companyId);

  if (!activeCompany) return <EmptyCompanyState icon={LayoutDashboard} />;

  const totalReceivables = receivables?.reduce((sum, r) => sum + parseFloat(r.outstanding), 0) ?? null;
  const totalPayables = payables?.reduce((sum, p) => sum + parseFloat(p.outstanding), 0) ?? null;
  const cashAndBank = trialBalance?.lines
    .filter((l) => l.ledger_type === "CASH" || l.ledger_type === "BANK")
    .reduce((sum, l) => sum + (l.balance_type === "DEBIT" ? parseFloat(l.balance) : -parseFloat(l.balance)), 0) ?? null;
  const pendingImports = imports?.items.filter((j) => PENDING_STATUSES.has(j.status)).length ?? null;
  const importErrors = imports?.items.reduce((sum, j) => sum + j.failed_rows, 0) ?? null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Accounting Dashboard</h1>
        <p className="text-sm text-muted-foreground">This month at a glance for {activeCompany.company_name}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard
          icon={ArrowUpCircle}
          iconClassName="text-success"
          label="Sales this period"
          isLoading={salesLoading}
          value={sales ? formatMoney(sales.grand_total) : "—"}
          hint={sales ? `${sales.invoice_count} invoice${sales.invoice_count === 1 ? "" : "s"}` : undefined}
        />
        <MetricCard
          icon={ArrowDownCircle}
          iconClassName="text-destructive"
          label="Purchases this period"
          isLoading={purchasesLoading}
          value={purchases ? formatMoney(purchases.grand_total) : "—"}
          hint={purchases ? `${purchases.invoice_count} invoice${purchases.invoice_count === 1 ? "" : "s"}` : undefined}
        />
        <MetricCard
          icon={Wallet}
          iconClassName="text-primary"
          label="Cash & bank position"
          isLoading={trialBalanceLoading}
          value={cashAndBank !== null ? formatMoney(cashAndBank.toFixed(2)) : "—"}
        />
        <MetricCard
          icon={ArrowUpCircle}
          iconClassName="text-warning"
          label="Receivables"
          isLoading={receivablesLoading}
          value={totalReceivables !== null ? formatMoney(totalReceivables.toFixed(2)) : "—"}
          linkTo="/accounting/reports"
        />
        <MetricCard
          icon={ArrowDownCircle}
          iconClassName="text-warning"
          label="Payables"
          isLoading={payablesLoading}
          value={totalPayables !== null ? formatMoney(totalPayables.toFixed(2)) : "—"}
          linkTo="/accounting/reports"
        />
        <MetricCard
          icon={UploadCloud}
          label="Pending imports"
          isLoading={importsLoading}
          value={pendingImports !== null ? String(pendingImports) : "—"}
          linkTo="/accounting/imports"
        />
      </div>

      {importErrors !== null && importErrors > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-destructive" /> Import errors need attention
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {importErrors} row{importErrors === 1 ? "" : "s"} failed validation across your import jobs.{" "}
              <Link to="/accounting/imports" className="font-medium text-primary hover:underline">
                Review imports
              </Link>
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function MetricCard({
  icon: Icon,
  iconClassName,
  label,
  value,
  hint,
  isLoading,
  linkTo,
}: {
  icon: React.ComponentType<{ className?: string }>;
  iconClassName?: string;
  label: string;
  value: string;
  hint?: string;
  isLoading: boolean;
  linkTo?: string;
}) {
  const content = (
    <Card className={linkTo ? "transition-colors hover:bg-accent/50" : undefined}>
      <CardContent className="flex items-start justify-between pt-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
          {isLoading ? (
            <Skeleton className="mt-2 h-7 w-24" />
          ) : (
            <p className="mt-1 text-xl font-semibold">{value}</p>
          )}
          {hint && !isLoading && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
        </div>
        <Icon className={`h-5 w-5 ${iconClassName ?? "text-muted-foreground"}`} />
      </CardContent>
    </Card>
  );
  return linkTo ? <Link to={linkTo}>{content}</Link> : content;
}
