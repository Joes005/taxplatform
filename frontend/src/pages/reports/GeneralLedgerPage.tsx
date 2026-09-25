import { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Layers,
  ArrowLeft,
  Building2,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useGeneralLedger } from "@/hooks/useBiReports";
import { ReportFilterBar } from "@/components/reports/ReportFilterBar";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
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

export default function GeneralLedgerPage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;
  const [searchParams] = useSearchParams();

  const ledgerId = searchParams.get("ledger_id") || undefined;
  const [filterParams, setFilterParams] = useState<{
    date_from?: string;
    date_to?: string;
  }>({});

  const { data: report, isLoading } = useGeneralLedger(companyId, ledgerId, filterParams);

  if (!companyId) {
    return (
      <div className="p-8 text-center bg-white rounded-lg border">
        <Building2 className="h-10 w-10 text-slate-400 mx-auto mb-2" />
        <p className="text-slate-600 font-medium">Please select an active company to view General Ledger.</p>
      </div>
    );
  }

  if (!ledgerId) {
    return (
      <div className="p-8 text-center bg-white rounded-lg border space-y-4">
        <Layers className="h-10 w-10 text-slate-400 mx-auto" />
        <div>
          <h2 className="text-base font-semibold text-slate-800">No Ledger Selected</h2>
          <p className="text-xs text-slate-500 mt-1">
            Please open the Trial Balance report to select a specific ledger for detailed ledger inspection.
          </p>
        </div>
        <Link to="/reports/financial?tab=trial-balance">
          <Button size="sm">Go to Trial Balance</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b pb-4">
        <div className="flex items-center gap-3">
          <Link to="/reports/financial?tab=trial-balance">
            <Button variant="outline" size="sm" className="h-8 px-2.5">
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                General Ledger: {report?.ledger_name || "Loading..."}
              </h1>
              {report?.ledger_type && (
                <Badge variant="outline" className="text-xs">
                  {report.ledger_type}
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Auditable chronological ledger statement with running balances and voucher drill-down.
            </p>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <ReportFilterBar
        companyId={companyId}
        reportType="GENERAL_LEDGER"
        showDateRange={true}
        onFilterChange={setFilterParams}
      />

      {isLoading && <Skeleton className="h-96 rounded-lg" />}

      {!isLoading && report && (
        <div className="space-y-6">
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card className="p-3">
              <div className="text-[11px] text-slate-500 font-semibold">Opening Balance</div>
              <div className="text-sm font-bold text-slate-900 mt-1">
                {formatCurrency(report.opening_balance)} ({report.opening_balance_type})
              </div>
            </Card>
            <Card className="p-3">
              <div className="text-[11px] text-slate-500 font-semibold">Total Debit</div>
              <div className="text-sm font-bold text-slate-900 mt-1">
                {formatCurrency(report.total_debit)}
              </div>
            </Card>
            <Card className="p-3">
              <div className="text-[11px] text-slate-500 font-semibold">Total Credit</div>
              <div className="text-sm font-bold text-slate-900 mt-1">
                {formatCurrency(report.total_credit)}
              </div>
            </Card>
            <Card className="p-3">
              <div className="text-[11px] text-slate-500 font-semibold">Closing Balance</div>
              <div className="text-sm font-bold text-blue-700 mt-1">
                {formatCurrency(report.closing_balance)} ({report.closing_balance_type})
              </div>
            </Card>
          </div>

          {/* Ledger Entries Table */}
          <div className="bg-white border rounded-lg overflow-hidden shadow-xs">
            <Table>
              <TableHeader className="bg-slate-50">
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Voucher #</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Debit</TableHead>
                  <TableHead className="text-right">Credit</TableHead>
                  <TableHead className="text-right">Running Balance</TableHead>
                  <TableHead className="text-center">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="text-xs">
                {report.entries.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-slate-400">
                      No posted journal entries found for this ledger in the selected period.
                    </TableCell>
                  </TableRow>
                ) : (
                  report.entries.map((entry) => (
                    <TableRow key={entry.id} className="hover:bg-slate-50">
                      <TableCell>{entry.date}</TableCell>
                      <TableCell className="font-mono font-medium">{entry.voucher_number}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-[10px] py-0">
                          {entry.voucher_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-600 max-w-xs truncate">{entry.description || "-"}</TableCell>
                      <TableCell className="text-right font-medium">{formatCurrency(entry.debit)}</TableCell>
                      <TableCell className="text-right font-medium">{formatCurrency(entry.credit)}</TableCell>
                      <TableCell className="text-right font-bold text-slate-900">
                        {formatCurrency(entry.running_balance)}
                      </TableCell>
                      <TableCell className="text-center">
                        {entry.drill_down_url ? (
                          <Link
                            to={entry.drill_down_url}
                            className="text-blue-600 hover:text-blue-800 font-semibold"
                          >
                            View
                          </Link>
                        ) : (
                          <span className="text-slate-300">-</span>
                        )}
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
