import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowDownRight,
  AlertCircle,
  Building2,
  Calendar,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useManagementDashboard } from "@/hooks/useBiReports";
import { ReportFilterBar } from "@/components/reports/ReportFilterBar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

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

export default function ManagementDashboardPage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;

  const [filterParams, setFilterParams] = useState<{
    date_from?: string;
    date_to?: string;
  }>({});

  const { data: report, isLoading, error } = useManagementDashboard(companyId, filterParams);

  if (!companyId) {
    return (
      <div className="p-8 text-center bg-white rounded-lg border">
        <Building2 className="h-10 w-10 text-slate-400 mx-auto mb-2" />
        <p className="text-slate-600 font-medium">Please select an active company to view Management Intelligence.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Executive Business Cockpit
            </h1>
            <Badge className="bg-indigo-600 text-white font-normal text-xs">
              Live BI
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Real-time authoritative executive overview with drill-down traceability and financial integrity.
          </p>
        </div>

        {report?.metadata && (
          <div className="text-xs text-slate-400 flex items-center gap-1.5 self-start md:self-auto bg-slate-50 px-3 py-1.5 rounded border">
            <Calendar className="h-3.5 w-3.5" />
            <span>Generated: {new Date(report.metadata.generated_at).toLocaleString()}</span>
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <ReportFilterBar
        companyId={companyId}
        reportType="MANAGEMENT"
        showDateRange={true}
        onFilterChange={(filters) => {
          setFilterParams({
            date_from: filters.date_from,
            date_to: filters.date_to,
          });
        }}
      />

      {/* Error state */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load management report</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : "An unexpected error occurred while compiling report data."}
          </AlertDescription>
        </Alert>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-64 rounded-lg" />
        </div>
      )}

      {/* Main Dashboard Content */}
      {!isLoading && report && (
        <div className="space-y-6">
          {/* KPI Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {report.cards.map((card) => {
              const isPositive = card.status === "POSITIVE";
              const isNegative = card.status === "NEGATIVE";

              return (
                <Card key={card.key} className="border-slate-200 hover:border-slate-300 transition-colors shadow-xs">
                  <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                    <CardTitle className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                      {card.label}
                    </CardTitle>
                    {card.change_percentage && (
                      <span
                        className={`text-xs font-semibold inline-flex items-center px-1.5 py-0.5 rounded ${
                          card.change_percentage === "N/A"
                            ? "bg-slate-100 text-slate-600"
                            : isPositive
                            ? "bg-emerald-50 text-emerald-700"
                            : isNegative
                            ? "bg-rose-50 text-rose-700"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {card.change_percentage.startsWith("+") && <ArrowUpRight className="h-3 w-3 mr-0.5" />}
                        {card.change_percentage.startsWith("-") && <ArrowDownRight className="h-3 w-3 mr-0.5" />}
                        {card.change_percentage}
                      </span>
                    )}
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="text-xl font-bold text-slate-900 tracking-tight">
                      {formatCurrency(card.current_value)}
                    </div>
                    <div className="mt-2 pt-2 border-t flex items-center justify-between text-xs">
                      {card.previous_value !== null && card.previous_value !== undefined && (
                        <span className="text-slate-400">
                          Prev: {formatCurrency(card.previous_value)}
                        </span>
                      )}
                      <Link
                        to={card.drill_down_url}
                        className="text-blue-600 hover:text-blue-800 font-medium ml-auto flex items-center"
                      >
                        Drill Down &rarr;
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Operational Risk & Compliance Snapshot */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="border-slate-200 shadow-xs">
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-semibold text-slate-800">
                    Open Audit Observations
                  </CardTitle>
                  <p className="text-xs text-slate-500">Unresolved statutory & internal audit findings</p>
                </div>
                <Badge
                  variant={report.audit_findings_count > 0 ? "destructive" : "secondary"}
                  className="font-bold"
                >
                  {report.audit_findings_count} Open
                </Badge>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center justify-between text-xs pt-2 border-t">
                  <span className="text-slate-500">Requires audit committee / management review</span>
                  <Link to="/reports/audit" className="text-blue-600 hover:text-blue-800 font-medium">
                    View Audit Dashboard &rarr;
                  </Link>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200 shadow-xs">
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-semibold text-slate-800">
                    Overdue Compliance Obligations
                  </CardTitle>
                  <p className="text-xs text-slate-500">Statutory GST/TDS/Income Tax filings past deadline</p>
                </div>
                <Badge
                  variant={report.overdue_compliance_count > 0 ? "destructive" : "secondary"}
                  className="font-bold"
                >
                  {report.overdue_compliance_count} Overdue
                </Badge>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center justify-between text-xs pt-2 border-t">
                  <span className="text-slate-500">Pending statutory obligations</span>
                  <Link to="/reports/compliance" className="text-blue-600 hover:text-blue-800 font-medium">
                    View Compliance Calendar &rarr;
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Top Outstanding Debtors & Creditors */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Debtors */}
            <Card className="border-slate-200 shadow-xs">
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold text-slate-800">
                  Key Accounts Receivable (Debtors)
                </CardTitle>
                <Link to="/reports/financial?tab=receivables" className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                  View All &rarr;
                </Link>
              </CardHeader>
              <CardContent className="pt-0">
                {report.top_receivables.length === 0 ? (
                  <p className="text-xs text-slate-400 py-4 text-center">No outstanding customer invoices recorded.</p>
                ) : (
                  <div className="divide-y text-xs">
                    {report.top_receivables.map((p) => (
                      <div key={p.party_id} className="py-2.5 flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-slate-800">{p.party_name}</div>
                          <div className="text-[11px] text-slate-400">
                            {p.invoice_count} invoice{p.invoice_count !== 1 ? "s" : ""}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-slate-900">{formatCurrency(p.outstanding)}</div>
                          {parseFloat(String(p.overdue_amount)) > 0 && (
                            <div className="text-[11px] text-rose-600 font-medium">
                              {formatCurrency(p.overdue_amount)} overdue
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Top Creditors */}
            <Card className="border-slate-200 shadow-xs">
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold text-slate-800">
                  Key Accounts Payable (Creditors)
                </CardTitle>
                <Link to="/reports/financial?tab=payables" className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                  View All &rarr;
                </Link>
              </CardHeader>
              <CardContent className="pt-0">
                {report.top_payables.length === 0 ? (
                  <p className="text-xs text-slate-400 py-4 text-center">No outstanding vendor bills recorded.</p>
                ) : (
                  <div className="divide-y text-xs">
                    {report.top_payables.map((p) => (
                      <div key={p.party_id} className="py-2.5 flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-slate-800">{p.party_name}</div>
                          <div className="text-[11px] text-slate-400">
                            {p.invoice_count} bill{p.invoice_count !== 1 ? "s" : ""}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-slate-900">{formatCurrency(p.outstanding)}</div>
                          {parseFloat(String(p.overdue_amount)) > 0 && (
                            <div className="text-[11px] text-amber-600 font-medium">
                              {formatCurrency(p.overdue_amount)} overdue
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
