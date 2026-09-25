import { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  ShieldCheck,
  Receipt,
  FileCheck2,
  CalendarClock,
  Building2,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import {
  useGstSummary,
  useTdsSummary,
  useAuditSummary,
  useComplianceSummary,
} from "@/hooks/useBiReports";
import { ReportFilterBar } from "@/components/reports/ReportFilterBar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
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

export default function TaxComplianceReportsPage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;
  const [searchParams, setSearchParams] = useSearchParams();

  const tab = searchParams.get("tab") || "gst";
  const [filterParams, setFilterParams] = useState<{
    date_from?: string;
    date_to?: string;
  }>({});

  const setTab = (newTab: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", newTab);
    setSearchParams(next);
  };

  const gstQuery = useGstSummary(tab === "gst" ? companyId : undefined, filterParams);
  const tdsQuery = useTdsSummary(tab === "tds" ? companyId : undefined, filterParams);
  const auditQuery = useAuditSummary(tab === "audit" ? companyId : undefined);
  const compQuery = useComplianceSummary(tab === "compliance" ? companyId : undefined);

  if (!companyId) {
    return (
      <div className="p-8 text-center bg-white rounded-lg border">
        <Building2 className="h-10 w-10 text-slate-400 mx-auto mb-2" />
        <p className="text-slate-600 font-medium">Please select an active company to view Tax & Compliance Reports.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b pb-4">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Tax & Compliance Business Intelligence
          </h1>
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            Statutory Assurance
          </Badge>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Automated GST position, TDS deduction & challan tracking, and audit/compliance analytics.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b space-x-1 overflow-x-auto bg-slate-50 p-1 rounded-lg">
        {[
          { id: "gst", label: "GST Summary", icon: ShieldCheck },
          { id: "tds", label: "TDS Intelligence", icon: Receipt },
          { id: "audit", label: "Audit Engagements", icon: FileCheck2 },
          { id: "compliance", label: "Compliance Calendar", icon: CalendarClock },
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
        reportType={tab === "gst" ? "GST" : tab === "tds" ? "TDS" : tab === "audit" ? "AUDIT" : "COMPLIANCE"}
        showDateRange={tab === "gst" || tab === "tds"}
        onFilterChange={setFilterParams}
      />

      {/* ---------------- 1. GST TAB ---------------- */}
      {tab === "gst" && (
        <div>
          {gstQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {gstQuery.data && (
            <div className="space-y-6">
              {/* Top Metrics Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Total Output Tax</div>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {formatCurrency(gstQuery.data.total_output_tax)}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    From {formatCurrency(gstQuery.data.outward_taxable)} taxable sales
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Eligible Input Tax Credit (ITC)</div>
                  <div className="text-xl font-bold text-emerald-600 mt-1">
                    {formatCurrency(gstQuery.data.total_eligible_itc)}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    From {formatCurrency(gstQuery.data.inward_taxable)} eligible inward purchases
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Net GST Payable</div>
                  <div className="text-xl font-bold text-blue-700 mt-1">
                    {formatCurrency(gstQuery.data.net_gst_payable)}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Output Tax minus Eligible ITC</div>
                </Card>
              </div>

              {/* GST Breakdown Table */}
              <Card>
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <CardTitle className="text-sm font-semibold">Tax Component Breakdown</CardTitle>
                  <Link to="/gst" className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                    Go to GST Module &rarr;
                  </Link>
                </CardHeader>
                <CardContent className="pt-0">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow>
                        <TableHead>Component</TableHead>
                        <TableHead className="text-right">CGST</TableHead>
                        <TableHead className="text-right">SGST</TableHead>
                        <TableHead className="text-right">IGST</TableHead>
                        <TableHead className="text-right">Cess</TableHead>
                        <TableHead className="text-right">Total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="text-xs">
                      <TableRow>
                        <TableCell className="font-semibold text-slate-800">Output Tax Liability</TableCell>
                        <TableCell className="text-right">{formatCurrency(gstQuery.data.cgst_outward)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(gstQuery.data.sgst_outward)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(gstQuery.data.igst_outward)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(gstQuery.data.cess_outward)}</TableCell>
                        <TableCell className="text-right font-bold text-slate-900">{formatCurrency(gstQuery.data.total_output_tax)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-semibold text-slate-800">Input Tax Credit (ITC)</TableCell>
                        <TableCell className="text-right text-emerald-600">{formatCurrency(gstQuery.data.eligible_itc_cgst)}</TableCell>
                        <TableCell className="text-right text-emerald-600">{formatCurrency(gstQuery.data.eligible_itc_sgst)}</TableCell>
                        <TableCell className="text-right text-emerald-600">{formatCurrency(gstQuery.data.eligible_itc_igst)}</TableCell>
                        <TableCell className="text-right text-emerald-600">{formatCurrency(gstQuery.data.eligible_itc_cess)}</TableCell>
                        <TableCell className="text-right font-bold text-emerald-700">{formatCurrency(gstQuery.data.total_eligible_itc)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ---------------- 2. TDS TAB ---------------- */}
      {tab === "tds" && (
        <div>
          {tdsQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {tdsQuery.data && (
            <div className="space-y-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">TDS Calculated</div>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {formatCurrency(tdsQuery.data.total_tds_calculated)}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">TDS Deducted</div>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {formatCurrency(tdsQuery.data.total_tds_deducted)}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Challan Deposited</div>
                  <div className="text-xl font-bold text-emerald-600 mt-1">
                    {formatCurrency(tdsQuery.data.challan_deposited_amount)}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">TDS Payable (Net)</div>
                  <div className="text-xl font-bold text-rose-600 mt-1">
                    {formatCurrency(tdsQuery.data.total_tds_payable)}
                  </div>
                </Card>
              </div>

              {/* Sections Breakdown */}
              <Card>
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <CardTitle className="text-sm font-semibold">TDS Sections Breakdown</CardTitle>
                  <Link to="/tds" className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                    Go to TDS Module &rarr;
                  </Link>
                </CardHeader>
                <CardContent className="pt-0">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow>
                        <TableHead>Section</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead className="text-center">Count</TableHead>
                        <TableHead className="text-right">Transaction Amount</TableHead>
                        <TableHead className="text-right">TDS Calculated</TableHead>
                        <TableHead className="text-right">TDS Deducted</TableHead>
                        <TableHead className="text-right">TDS Payable</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="text-xs">
                      {tdsQuery.data.sections.map((sec, i) => (
                        <TableRow key={i}>
                          <TableCell className="font-mono font-bold text-blue-700">{sec.section_code}</TableCell>
                          <TableCell className="text-slate-600">{sec.section_description}</TableCell>
                          <TableCell className="text-center">{sec.transaction_count}</TableCell>
                          <TableCell className="text-right">{formatCurrency(sec.total_amount)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(sec.tds_calculated)}</TableCell>
                          <TableCell className="text-right font-medium">{formatCurrency(sec.tds_deducted)}</TableCell>
                          <TableCell className="text-right font-bold text-rose-600">{formatCurrency(sec.tds_payable)}</TableCell>
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

      {/* ---------------- 3. AUDIT TAB ---------------- */}
      {tab === "audit" && (
        <div>
          {auditQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {auditQuery.data && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Engagements</div>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {auditQuery.data.total_engagements}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {auditQuery.data.open_engagements} open, {auditQuery.data.completed_engagements} completed
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Checklist Completion</div>
                  <div className="text-xl font-bold text-emerald-600 mt-1">
                    {auditQuery.data.checklist_completion_rate}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {auditQuery.data.checklist_completed} of {auditQuery.data.checklist_total} verified
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Total Findings</div>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {auditQuery.data.total_findings}
                  </div>
                  <div className="text-[11px] text-rose-600 font-semibold mt-0.5">
                    {auditQuery.data.open_findings} open ({auditQuery.data.critical_findings} critical)
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Signed-off Engagements</div>
                  <div className="text-xl font-bold text-blue-700 mt-1">
                    {auditQuery.data.signed_off_count}
                  </div>
                </Card>
              </div>

              <Card>
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <CardTitle className="text-sm font-semibold">Auditor Review Queue</CardTitle>
                  <Link to="/audits" className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                    Open Audit Module &rarr;
                  </Link>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="divide-y text-xs">
                    <div className="py-2.5 flex justify-between">
                      <span className="text-slate-600">Pending Evidence Submissions</span>
                      <Badge variant="outline">{auditQuery.data.pending_evidence}</Badge>
                    </div>
                    <div className="py-2.5 flex justify-between">
                      <span className="text-slate-600">Pending Management Responses</span>
                      <Badge variant="outline">{auditQuery.data.pending_responses}</Badge>
                    </div>
                    <div className="py-2.5 flex justify-between">
                      <span className="text-slate-600">Pending Auditor Final Review</span>
                      <Badge variant="outline">{auditQuery.data.pending_review}</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ---------------- 4. COMPLIANCE TAB ---------------- */}
      {tab === "compliance" && (
        <div>
          {compQuery.isLoading && <Skeleton className="h-96 rounded-lg" />}
          {compQuery.data && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Active Obligations</div>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {compQuery.data.active_obligations}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Completed Tasks</div>
                  <div className="text-xl font-bold text-emerald-600 mt-1">
                    {compQuery.data.completed_tasks}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Due Soon Tasks</div>
                  <div className="text-xl font-bold text-amber-600 mt-1">
                    {compQuery.data.due_soon_tasks}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-500 font-semibold">Overdue Tasks</div>
                  <div className="text-xl font-bold text-rose-600 mt-1">
                    {compQuery.data.overdue_tasks}
                  </div>
                </Card>
              </div>

              <Card>
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <CardTitle className="text-sm font-semibold">Category-wise Compliance Health</CardTitle>
                  <Link to="/compliance" className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                    Open Compliance Calendar &rarr;
                  </Link>
                </CardHeader>
                <CardContent className="pt-0">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow>
                        <TableHead>Category</TableHead>
                        <TableHead className="text-center">Total Tasks</TableHead>
                        <TableHead className="text-center">Completed</TableHead>
                        <TableHead className="text-center">Overdue</TableHead>
                        <TableHead className="text-center">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="text-xs">
                      {compQuery.data.categories.map((c, i) => (
                        <TableRow key={i}>
                          <TableCell className="font-semibold text-slate-800">{c.category}</TableCell>
                          <TableCell className="text-center">{c.total}</TableCell>
                          <TableCell className="text-center text-emerald-600 font-medium">{c.completed}</TableCell>
                          <TableCell className="text-center text-rose-600 font-medium">{c.overdue}</TableCell>
                          <TableCell className="text-center">
                            {c.overdue > 0 ? (
                              <Badge variant="destructive" className="text-[10px]">Overdue</Badge>
                            ) : (
                              <Badge variant="outline" className="text-[10px] text-emerald-700 bg-emerald-50">On Track</Badge>
                            )}
                          </TableCell>
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
