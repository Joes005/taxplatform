import { useState } from "react";
import { Link } from "react-router-dom";
import {
  FileCheck2,
  Building2,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useCashBank } from "@/hooks/useBiReports";
import { ReportFilterBar } from "@/components/reports/ReportFilterBar";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

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

export default function BankingReportsPage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;

  const [filterParams, setFilterParams] = useState<{
    date_from?: string;
    date_to?: string;
  }>({});

  const { data: report, isLoading } = useCashBank(companyId, filterParams);

  if (!companyId) {
    return (
      <div className="p-8 text-center bg-white rounded-lg border">
        <Building2 className="h-10 w-10 text-slate-400 mx-auto mb-2" />
        <p className="text-slate-600 font-medium">Please select an active company to view Banking Reports.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b pb-4">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Cash & Bank Reconciliation Intelligence
          </h1>
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            Liquidity & Cash Flow
          </Badge>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Account balances, collections, disbursements, and statement reconciliation status.
        </p>
      </div>

      {/* Filter Bar */}
      <ReportFilterBar
        companyId={companyId}
        reportType="CASH_BANK"
        showDateRange={true}
        onFilterChange={setFilterParams}
      />

      {isLoading && <Skeleton className="h-96 rounded-lg" />}

      {!isLoading && report && (
        <div className="space-y-6">
          {/* Top Summary */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <Card className="p-4">
              <div className="text-xs text-slate-500 font-semibold">Opening Bank Balance</div>
              <div className="text-xl font-bold text-slate-900 mt-1">
                {formatCurrency(report.total_opening_balance)}
              </div>
            </Card>
            <Card className="p-4">
              <div className="text-xs text-slate-500 font-semibold">Total Collections (Inflows)</div>
              <div className="text-xl font-bold text-emerald-600 mt-1">
                {formatCurrency(report.total_receipts)}
              </div>
            </Card>
            <Card className="p-4">
              <div className="text-xs text-slate-500 font-semibold">Total Disbursements (Outflows)</div>
              <div className="text-xl font-bold text-rose-600 mt-1">
                {formatCurrency(report.total_payments)}
              </div>
            </Card>
            <Card className="p-4">
              <div className="text-xs text-slate-500 font-semibold">Closing Bank Balance</div>
              <div className="text-xl font-bold text-blue-700 mt-1">
                {formatCurrency(report.total_closing_balance)}
              </div>
            </Card>
          </div>

          {/* Reconciliation Status Badge */}
          <div className="bg-white border rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                <FileCheck2 className="h-5 w-5" />
              </div>
              <div>
                <div className="text-sm font-semibold text-slate-900">
                  Bank Reconciliation Status: {report.reconciliation_status}
                </div>
                <div className="text-xs text-slate-500">
                  {report.matched_transactions} matched transactions, {report.unmatched_transactions} unmatched
                </div>
              </div>
            </div>
            <Link to="/bank/reconciliations" className="text-xs font-semibold text-blue-600 hover:text-blue-800">
              Open Reconciliations &rarr;
            </Link>
          </div>

          {/* Accounts Breakdown Table */}
          <div className="bg-white border rounded-lg overflow-hidden shadow-xs">
            <Table>
              <TableHeader className="bg-slate-50">
                <TableRow>
                  <TableHead>Bank Account</TableHead>
                  <TableHead>Account #</TableHead>
                  <TableHead className="text-right">Opening Balance</TableHead>
                  <TableHead className="text-right">Receipts</TableHead>
                  <TableHead className="text-right">Payments</TableHead>
                  <TableHead className="text-right">Closing Balance</TableHead>
                  <TableHead className="text-center">Unreconciled</TableHead>
                  <TableHead className="text-center">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="text-xs">
                {report.accounts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-slate-400">
                      No active bank accounts found.
                    </TableCell>
                  </TableRow>
                ) : (
                  report.accounts.map((acc) => (
                    <TableRow key={acc.account_id} className="hover:bg-slate-50">
                      <TableCell className="font-semibold text-slate-800">{acc.bank_name}</TableCell>
                      <TableCell className="font-mono text-slate-600">{acc.account_number}</TableCell>
                      <TableCell className="text-right">{formatCurrency(acc.opening_balance)}</TableCell>
                      <TableCell className="text-right text-emerald-600">{formatCurrency(acc.receipts)}</TableCell>
                      <TableCell className="text-right text-rose-600">{formatCurrency(acc.payments)}</TableCell>
                      <TableCell className="text-right font-bold text-blue-700">{formatCurrency(acc.closing_balance)}</TableCell>
                      <TableCell className="text-center">
                        {acc.unreconciled_items_count > 0 ? (
                          <Badge variant="destructive" className="text-[10px]">
                            {acc.unreconciled_items_count} items
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-[10px] text-emerald-700 bg-emerald-50">
                            Reconciled
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Link
                          to={acc.drill_down_url}
                          className="text-blue-600 hover:text-blue-800 font-semibold"
                        >
                          View Transactions
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}
