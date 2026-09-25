import { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Scale,
  TrendingUp,
  Layers,
  UsersRound,
  Truck,
  Clock,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  Building2,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import {
  useTrialBalance,
  useProfitLoss,
  useBalanceSheet,
  useReceivables,
  usePayables,
  useAgeing,
  useSalesAnalytics,
} from "@/hooks/useBiReports";
import { ReportFilterBar } from "@/components/reports/ReportFilterBar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

function formatCurrency(val: string | number | undefined) {
  if (val === undefined || val === null) return "₹0.00";
  const num = typeof val === "number" ? val : parseFloat(val);
  if (isNaN(num)) return "₹0.00";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(num);
}

export default function FinancialReportsPage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;
  const [searchParams, setSearchParams] = useSearchParams();

  const tab = searchParams.get("tab") || "trial-balance";
  const [filterParams, setFilterParams] = useState<{
    date_from?: string;
    date_to?: string;
    as_of?: string;
    compare_previous?: boolean;
  }>({});

  const setTab = (newTab: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", newTab);
    setSearchParams(next);
  };

  // Queries for active tab
  const tbQuery = useTrialBalance(
    tab === "trial-balance" ? companyId : undefined,
    { as_of: filterParams.as_of }
  );
  const pnlQuery = useProfitLoss(
    tab === "profit-loss" ? companyId : undefined,
    {
      date_from: filterParams.date_from,
      date_to: filterParams.date_to,
      compare_previous: filterParams.compare_previous,
    }
  );
  const bsQuery = useBalanceSheet(
    tab === "balance-sheet" ? companyId : undefined,
    { as_of: filterParams.as_of }
  );
  const recQuery = useReceivables(
    tab === "receivables" ? companyId : undefined,
    { date_from: filterParams.date_from, date_to: filterParams.date_to }
  );
  const payQuery = usePayables(
    tab === "payables" ? companyId : undefined,
    { date_from: filterParams.date_from, date_to: filterParams.date_to }
  );

  const [ageingKind, setAgeingKind] = useState<"RECEIVABLES" | "PAYABLES">("RECEIVABLES");
  const ageingQuery = useAgeing(
    tab === "ageing" ? companyId : undefined,
    ageingKind,
    filterParams.as_of
  );

  const salesAnalyticsQuery = useSalesAnalytics(
    tab === "sales-analytics" ? companyId : undefined,
    { date_from: filterParams.date_from, date_to: filterParams.date_to }
  );

  if (!companyId) {
    return (
      <div className="p-8 text-center bg-white rounded-lg border">
        <Building2 className="h-10 w-10 text-slate-400 mx-auto mb-2" />
        <p className="text-slate-600 font-medium">Please select an active company to view Financial Reports.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b pb-4">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Financial & Accounting Intelligence
          </h1>
          <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
            Double Entry Integrity
          </Badge>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Standardized Trial Balance, P&L, Balance Sheet, Ledger drill-down, and Party Outstanding.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b space-x-1 overflow-x-auto bg-slate-50 p-1 rounded-lg">
        {[
          { id: "trial-balance", label: "Trial Balance", icon: Scale },
          { id: "profit-loss", label: "Profit & Loss", icon: TrendingUp },
          { id: "balance-sheet", label: "Balance Sheet", icon: Layers },
          { id: "receivables", label: "Receivables", icon: UsersRound },
          { id: "payables", label: "Payables", icon: Truck },
          { id: "ageing", label: "Ageing Analysis", icon: Clock },
          { id: "sales-analytics", label: "Sales Analytics", icon: BarChart3 },
        ].map((t) => {
          const Icon = t.icon;
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-md whitespace-nowrap transition-colors ${
                isActive
                  ? "bg-white text-slate-900 shadow-xs border"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Filter Bar */}
      <ReportFilterBar
        companyId={companyId}
        reportType={
          tab === "trial-balance"
            ? "TRIAL_BALANCE"
            : tab === "profit-loss"
            ? "PROFIT_LOSS"
            : tab === "balance-sheet"
            ? "BALANCE_SHEET"
            : tab === "receivables"
            ? "RECEIVABLES"
            : tab === "payables"
            ? "PAYABLES"
            : tab === "ageing"
            ? "AGEING"
            : "SALES"
        }
        showAsOf={tab === "trial-balance" || tab === "balance-sheet" || tab === "ageing"}
        showDateRange={tab !== "balance-sheet" && tab !== "trial-balance" && tab !== "ageing"}
        showCompare={tab === "profit-loss"}
        onFilterChange={setFilterParams}
      />

      {/* ---------------- 1. TRIAL BALANCE TAB ---------------- */}
      {tab === "trial-balance" && (
        <div>
          {tbQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {tbQuery.data && (
            <div className="space-y-4">
              {/* Integrity Warning / Pass Banner */}
              {tbQuery.data.is_balanced ? (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span>
                    <strong>Double-entry verification passed:</strong> Total Debit equals Total Credit. Difference is ₹0.00.
                  </span>
                </div>
              ) : (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Integrity Warning: Trial Balance Out of Balance!</AlertTitle>
                  <AlertDescription>
                    {tbQuery.data.integrity_warning || `Debit and Credit differ by ${formatCurrency(tbQuery.data.difference)}.`}
                  </AlertDescription>
                </Alert>
              )}

              <div className="bg-white border rounded-lg overflow-hidden shadow-xs">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead>Ledger</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Opening Dr</TableHead>
                      <TableHead className="text-right">Opening Cr</TableHead>
                      <TableHead className="text-right">Period Dr</TableHead>
                      <TableHead className="text-right">Period Cr</TableHead>
                      <TableHead className="text-right">Closing Dr</TableHead>
                      <TableHead className="text-right">Closing Cr</TableHead>
                      <TableHead className="text-center">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="text-xs">
                    {tbQuery.data.lines.map((line) => (
                      <TableRow key={line.ledger_id} className="hover:bg-slate-50">
                        <TableCell className="font-semibold text-slate-800">{line.ledger_name}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-[10px] py-0">
                            {line.ledger_type}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">{formatCurrency(line.opening_debit)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(line.opening_credit)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(line.period_debit)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(line.period_credit)}</TableCell>
                        <TableCell className="text-right font-medium">{formatCurrency(line.closing_debit)}</TableCell>
                        <TableCell className="text-right font-medium">{formatCurrency(line.closing_credit)}</TableCell>
                        <TableCell className="text-center">
                          <Link
                            to={`/reports/general-ledger?ledger_id=${line.ledger_id}`}
                            className="text-blue-600 hover:text-blue-800 font-semibold"
                          >
                            View Ledger
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}

                    {/* Totals Row */}
                    <TableRow className="bg-slate-100 font-bold text-xs border-t-2">
                      <TableCell colSpan={2}>TOTAL</TableCell>
                      <TableCell className="text-right">{formatCurrency(tbQuery.data.total_opening_debit)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(tbQuery.data.total_opening_credit)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(tbQuery.data.total_period_debit)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(tbQuery.data.total_period_credit)}</TableCell>
                      <TableCell className="text-right text-slate-900">{formatCurrency(tbQuery.data.total_closing_debit)}</TableCell>
                      <TableCell className="text-right text-slate-900">{formatCurrency(tbQuery.data.total_closing_credit)}</TableCell>
                      <TableCell />
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---------------- 2. PROFIT & LOSS TAB ---------------- */}
      {tab === "profit-loss" && (
        <div>
          {pnlQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {pnlQuery.data && (
            <div className="space-y-6">
              {/* Classification Warnings */}
              {pnlQuery.data.classification_warnings.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
                  <div className="font-semibold flex items-center gap-1.5 mb-1">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    Classification Warnings
                  </div>
                  <ul className="list-disc pl-5 space-y-0.5">
                    {pnlQuery.data.classification_warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="bg-white border rounded-lg p-6 shadow-xs space-y-6">
                {/* Revenue Section */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    {pnlQuery.data.revenue_section.title}
                  </h3>
                  <div className="divide-y text-xs">
                    {pnlQuery.data.revenue_section.items.map((it, i) => (
                      <div key={i} className="py-2 flex justify-between">
                        <span>{it.name}</span>
                        <span className="font-medium">{formatCurrency(it.amount)}</span>
                      </div>
                    ))}
                    <div className="py-2 flex justify-between font-bold text-slate-900 bg-slate-50 px-2 rounded">
                      <span>Total Revenue</span>
                      <span>{formatCurrency(pnlQuery.data.revenue_section.subtotal)}</span>
                    </div>
                  </div>
                </div>

                {/* Direct Costs Section */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    {pnlQuery.data.direct_costs_section.title}
                  </h3>
                  <div className="divide-y text-xs">
                    {pnlQuery.data.direct_costs_section.items.map((it, i) => (
                      <div key={i} className="py-2 flex justify-between">
                        <span>{it.name}</span>
                        <span className="font-medium">{formatCurrency(it.amount)}</span>
                      </div>
                    ))}
                    <div className="py-2 flex justify-between font-bold text-slate-900 bg-slate-50 px-2 rounded">
                      <span>Total Cost of Sales</span>
                      <span>{formatCurrency(pnlQuery.data.direct_costs_section.subtotal)}</span>
                    </div>
                  </div>
                </div>

                {/* Gross Profit Row */}
                <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg flex justify-between font-bold text-sm text-blue-950">
                  <span>GROSS PROFIT</span>
                  <span>{formatCurrency(pnlQuery.data.gross_profit)}</span>
                </div>

                {/* Operating Expenses Section */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    {pnlQuery.data.operating_expenses_section.title}
                  </h3>
                  <div className="divide-y text-xs">
                    {pnlQuery.data.operating_expenses_section.items.map((it, i) => (
                      <div key={i} className="py-2 flex justify-between">
                        <span>{it.name}</span>
                        <span className="font-medium">{formatCurrency(it.amount)}</span>
                      </div>
                    ))}
                    <div className="py-2 flex justify-between font-bold text-slate-900 bg-slate-50 px-2 rounded">
                      <span>Total Operating Expenses</span>
                      <span>{formatCurrency(pnlQuery.data.operating_expenses_section.subtotal)}</span>
                    </div>
                  </div>
                </div>

                {/* Net Profit Row */}
                <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-lg flex justify-between font-bold text-base text-emerald-950">
                  <span>NET PROFIT / (LOSS)</span>
                  <span>{formatCurrency(pnlQuery.data.net_profit)}</span>
                </div>

                {/* Comparison Card if enabled */}
                {pnlQuery.data.comparison && (
                  <div className="border-t pt-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                      Period Comparison
                    </h4>
                    <div className="grid grid-cols-2 gap-4 text-xs">
                      {Object.entries(pnlQuery.data.comparison).map(([k, val]) => (
                        <div key={k} className="p-3 bg-slate-50 rounded border">
                          <div className="text-slate-500 uppercase font-semibold text-[11px]">{k}</div>
                          <div className="text-sm font-bold text-slate-900 mt-1">
                            Current: {formatCurrency(val.current)}
                          </div>
                          <div className="text-slate-400 mt-0.5">
                            Previous: {formatCurrency(val.previous)} | Change: {val.percentage_change}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---------------- 3. BALANCE SHEET TAB ---------------- */}
      {tab === "balance-sheet" && (
        <div>
          {bsQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {bsQuery.data && (
            <div className="space-y-6">
              {/* Balance Verification */}
              {bsQuery.data.is_balanced ? (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span>
                    <strong>Balance Sheet reconciled:</strong> Assets ({formatCurrency(bsQuery.data.total_assets)}) == Liabilities + Equity ({formatCurrency(bsQuery.data.total_liabilities_and_equity)}).
                  </span>
                </div>
              ) : (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Integrity Warning: Balance Sheet Unbalanced!</AlertTitle>
                  <AlertDescription>
                    {bsQuery.data.reconciliation_warning || `Difference of ${formatCurrency(bsQuery.data.difference)} between Assets and Liabilities+Equity.`}
                  </AlertDescription>
                </Alert>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Assets Column */}
                <div className="bg-white border rounded-lg p-5 shadow-xs space-y-4">
                  <h3 className="text-sm font-bold uppercase text-slate-800 border-b pb-2">Assets</h3>
                  {bsQuery.data.assets.map((sec, i) => (
                    <div key={i}>
                      <div className="font-semibold text-xs text-slate-600 mb-1">{sec.title}</div>
                      <div className="divide-y text-xs">
                        {sec.items.map((it, j) => (
                          <div key={j} className="py-1.5 flex justify-between">
                            <span>{it.name}</span>
                            <span className="font-medium">{formatCurrency(it.amount)}</span>
                          </div>
                        ))}
                        <div className="py-1 flex justify-between font-bold text-slate-800">
                          <span>Subtotal</span>
                          <span>{formatCurrency(sec.subtotal)}</span>
                        </div>
                      </div>
                    </div>
                  ))}

                  <div className="bg-slate-100 p-3 rounded font-bold text-sm flex justify-between text-slate-900 border-t-2">
                    <span>TOTAL ASSETS</span>
                    <span>{formatCurrency(bsQuery.data.total_assets)}</span>
                  </div>
                </div>

                {/* Liabilities & Equity Column */}
                <div className="bg-white border rounded-lg p-5 shadow-xs space-y-4">
                  <h3 className="text-sm font-bold uppercase text-slate-800 border-b pb-2">
                    Liabilities & Equity
                  </h3>

                  {/* Liabilities */}
                  {bsQuery.data.liabilities.map((sec, i) => (
                    <div key={i}>
                      <div className="font-semibold text-xs text-slate-600 mb-1">{sec.title}</div>
                      <div className="divide-y text-xs">
                        {sec.items.map((it, j) => (
                          <div key={j} className="py-1.5 flex justify-between">
                            <span>{it.name}</span>
                            <span className="font-medium">{formatCurrency(it.amount)}</span>
                          </div>
                        ))}
                        <div className="py-1 flex justify-between font-bold text-slate-800">
                          <span>Subtotal Liabilities</span>
                          <span>{formatCurrency(sec.subtotal)}</span>
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Equity */}
                  <div>
                    <div className="font-semibold text-xs text-slate-600 mb-1">Equity & Reserves</div>
                    <div className="divide-y text-xs">
                      {bsQuery.data.equity.flatMap((s) => s.items).map((it, j) => (
                        <div key={j} className="py-1.5 flex justify-between">
                          <span>{it.name}</span>
                          <span className="font-medium">{formatCurrency(it.amount)}</span>
                        </div>
                      ))}
                      <div className="py-1.5 flex justify-between font-medium">
                        <span>Retained Earnings (from P&L)</span>
                        <span>{formatCurrency(bsQuery.data.retained_earnings)}</span>
                      </div>
                      <div className="py-1 flex justify-between font-bold text-slate-800">
                        <span>Total Equity</span>
                        <span>{formatCurrency(bsQuery.data.total_equity)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-100 p-3 rounded font-bold text-sm flex justify-between text-slate-900 border-t-2">
                    <span>TOTAL LIABILITIES & EQUITY</span>
                    <span>{formatCurrency(bsQuery.data.total_liabilities_and_equity)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---------------- 4. RECEIVABLES TAB ---------------- */}
      {tab === "receivables" && (
        <div>
          {recQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {recQuery.data && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <Card className="p-3">
                  <div className="text-[11px] text-slate-500 font-semibold">Total Invoiced</div>
                  <div className="text-base font-bold text-slate-900 mt-1">
                    {formatCurrency(recQuery.data.total_invoiced)}
                  </div>
                </Card>
                <Card className="p-3">
                  <div className="text-[11px] text-slate-500 font-semibold">Total Settled</div>
                  <div className="text-base font-bold text-emerald-600 mt-1">
                    {formatCurrency(recQuery.data.total_settled)}
                  </div>
                </Card>
                <Card className="p-3">
                  <div className="text-[11px] text-slate-500 font-semibold">Total Outstanding</div>
                  <div className="text-base font-bold text-blue-600 mt-1">
                    {formatCurrency(recQuery.data.total_outstanding)}
                  </div>
                </Card>
                <Card className="p-3">
                  <div className="text-[11px] text-slate-500 font-semibold">Total Overdue</div>
                  <div className="text-base font-bold text-rose-600 mt-1">
                    {formatCurrency(recQuery.data.total_overdue)}
                  </div>
                </Card>
              </div>

              <div className="bg-white border rounded-lg overflow-hidden shadow-xs">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead>Customer</TableHead>
                      <TableHead className="text-center">Invoices</TableHead>
                      <TableHead className="text-right">Gross Invoiced</TableHead>
                      <TableHead className="text-right">Debit Notes</TableHead>
                      <TableHead className="text-right">Credit Notes</TableHead>
                      <TableHead className="text-right">Receipts</TableHead>
                      <TableHead className="text-right">Net Invoiced</TableHead>
                      <TableHead className="text-right">Outstanding</TableHead>
                      <TableHead className="text-right">Overdue</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="text-xs">
                    {recQuery.data.parties.map((p) => (
                      <TableRow key={p.party_id} className="hover:bg-slate-50">
                        <TableCell className="font-semibold text-slate-800">{p.party_name}</TableCell>
                        <TableCell className="text-center">{p.invoice_count}</TableCell>
                        <TableCell className="text-right">{formatCurrency(p.gross_invoiced)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(p.debit_notes)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(p.credit_notes)}</TableCell>
                        <TableCell className="text-right text-emerald-600">{formatCurrency(p.settled_amount)}</TableCell>
                        <TableCell className="text-right font-medium">{formatCurrency(p.net_invoiced)}</TableCell>
                        <TableCell className="text-right font-bold text-blue-700">{formatCurrency(p.outstanding)}</TableCell>
                        <TableCell className="text-right font-semibold text-rose-600">{formatCurrency(p.overdue_amount)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---------------- 5. PAYABLES TAB ---------------- */}
      {tab === "payables" && (
        <div>
          {payQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {payQuery.data && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <Card className="p-3">
                  <div className="text-[11px] text-slate-500 font-semibold">Total Invoiced</div>
                  <div className="text-base font-bold text-slate-900 mt-1">
                    {formatCurrency(payQuery.data.total_invoiced)}
                  </div>
                </Card>
                <Card className="p-3">
                  <div className="text-[11px] text-slate-500 font-semibold">Total Settled</div>
                  <div className="text-base font-bold text-emerald-600 mt-1">
                    {formatCurrency(payQuery.data.total_settled)}
                  </div>
                </Card>
                <Card className="p-3">
                  <div className="text-[11px] text-slate-500 font-semibold">Total Outstanding</div>
                  <div className="text-base font-bold text-blue-600 mt-1">
                    {formatCurrency(payQuery.data.total_outstanding)}
                  </div>
                </Card>
                <Card className="p-3">
                  <div className="text-[11px] text-slate-500 font-semibold">Total Overdue</div>
                  <div className="text-base font-bold text-rose-600 mt-1">
                    {formatCurrency(payQuery.data.total_overdue)}
                  </div>
                </Card>
              </div>

              <div className="bg-white border rounded-lg overflow-hidden shadow-xs">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead>Vendor</TableHead>
                      <TableHead className="text-center">Bills</TableHead>
                      <TableHead className="text-right">Gross Invoiced</TableHead>
                      <TableHead className="text-right">Debit Notes</TableHead>
                      <TableHead className="text-right">Credit Notes</TableHead>
                      <TableHead className="text-right">Payments</TableHead>
                      <TableHead className="text-right">Net Invoiced</TableHead>
                      <TableHead className="text-right">Outstanding</TableHead>
                      <TableHead className="text-right">Overdue</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="text-xs">
                    {payQuery.data.parties.map((p) => (
                      <TableRow key={p.party_id} className="hover:bg-slate-50">
                        <TableCell className="font-semibold text-slate-800">{p.party_name}</TableCell>
                        <TableCell className="text-center">{p.invoice_count}</TableCell>
                        <TableCell className="text-right">{formatCurrency(p.gross_invoiced)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(p.debit_notes)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(p.credit_notes)}</TableCell>
                        <TableCell className="text-right text-emerald-600">{formatCurrency(p.settled_amount)}</TableCell>
                        <TableCell className="text-right font-medium">{formatCurrency(p.net_invoiced)}</TableCell>
                        <TableCell className="text-right font-bold text-blue-700">{formatCurrency(p.outstanding)}</TableCell>
                        <TableCell className="text-right font-semibold text-rose-600">{formatCurrency(p.overdue_amount)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---------------- 6. AGEING TAB ---------------- */}
      {tab === "ageing" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={ageingKind === "RECEIVABLES" ? "default" : "outline"}
              onClick={() => setAgeingKind("RECEIVABLES")}
            >
              Receivables Ageing
            </Button>
            <Button
              size="sm"
              variant={ageingKind === "PAYABLES" ? "default" : "outline"}
              onClick={() => setAgeingKind("PAYABLES")}
            >
              Payables Ageing
            </Button>
          </div>

          {ageingQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {ageingQuery.data && (
            <div className="space-y-5">
              {/* Bucket summary cards */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {ageingQuery.data.bucket_summaries.map((b) => (
                  <Card key={b.bucket} className="p-3 border-slate-200">
                    <div className="text-[11px] font-semibold text-slate-500 uppercase">{b.label}</div>
                    <div className="text-sm font-bold text-slate-900 mt-1">
                      {formatCurrency(b.amount)}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{b.count} invoice{b.count !== 1 ? "s" : ""}</div>
                  </Card>
                ))}
              </div>

              {/* Invoices list */}
              <div className="bg-white border rounded-lg overflow-hidden shadow-xs">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead>Party</TableHead>
                      <TableHead>Invoice #</TableHead>
                      <TableHead>Invoice Date</TableHead>
                      <TableHead>Due Date</TableHead>
                      <TableHead className="text-right">Outstanding</TableHead>
                      <TableHead className="text-center">Days Overdue</TableHead>
                      <TableHead className="text-center">Bucket</TableHead>
                      <TableHead className="text-center">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="text-xs">
                    {ageingQuery.data.invoices.map((inv) => (
                      <TableRow key={inv.invoice_id} className="hover:bg-slate-50">
                        <TableCell className="font-semibold text-slate-800">{inv.party_name}</TableCell>
                        <TableCell className="font-mono">{inv.invoice_number}</TableCell>
                        <TableCell>{inv.invoice_date}</TableCell>
                        <TableCell>
                          {inv.due_date ? (
                            inv.due_date
                          ) : (
                            <span className="text-slate-400 italic">Fallback (Inv Date)</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-bold text-slate-900">
                          {formatCurrency(inv.outstanding_amount)}
                        </TableCell>
                        <TableCell className="text-center font-medium">
                          {inv.ageing_days > 0 ? (
                            <span className="text-rose-600 font-bold">{inv.ageing_days}d</span>
                          ) : (
                            <span className="text-emerald-600">Current</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="outline" className="text-[10px]">
                            {inv.bucket}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          <Link
                            to={inv.drill_down_url}
                            className="text-blue-600 hover:text-blue-800 font-semibold"
                          >
                            Drill Down
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---------------- 7. SALES ANALYTICS TAB ---------------- */}
      {tab === "sales-analytics" && (
        <div>
          {salesAnalyticsQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {salesAnalyticsQuery.data && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Gross Sales</div>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {formatCurrency(salesAnalyticsQuery.data.gross_total)}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Net Sales</div>
                  <div className="text-xl font-bold text-emerald-600 mt-1">
                    {formatCurrency(salesAnalyticsQuery.data.net_total)}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Invoices Count</div>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {salesAnalyticsQuery.data.invoice_count}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Avg Ticket Value</div>
                  <div className="text-xl font-bold text-blue-600 mt-1">
                    {formatCurrency(salesAnalyticsQuery.data.average_invoice_value)}
                  </div>
                </Card>
              </div>

              {/* GST Tax Slabs Breakdown */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold">GST Slab Distribution</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow>
                        <TableHead>GST Slab Rate</TableHead>
                        <TableHead className="text-right">Taxable Turnover</TableHead>
                        <TableHead className="text-right">CGST</TableHead>
                        <TableHead className="text-right">SGST</TableHead>
                        <TableHead className="text-right">IGST</TableHead>
                        <TableHead className="text-right">Total Tax</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="text-xs">
                      {salesAnalyticsQuery.data.gst_breakdown.map((b, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-semibold">{b.tax_rate}%</TableCell>
                          <TableCell className="text-right">{formatCurrency(b.taxable_amount)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(b.cgst)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(b.sgst)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(b.igst)}</TableCell>
                          <TableCell className="text-right font-bold">{formatCurrency(b.total_tax)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
