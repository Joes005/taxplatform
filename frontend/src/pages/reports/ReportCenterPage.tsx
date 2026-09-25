import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  BarChart3,
  TrendingUp,
  Scale,
  FileSpreadsheet,
  Layers,
  UsersRound,
  Truck,
  Clock,
  Landmark,
  ShieldCheck,
  Receipt,
  FileCheck2,
  CalendarClock,
  Search,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface ReportDef {
  id: string;
  name: string;
  description: string;
  category: "FINANCIAL" | "TAX" | "BANK" | "AUDIT" | "COMPLIANCE" | "MANAGEMENT";
  icon: React.ComponentType<{ className?: string }>;
  path: string;
  badge?: string;
  isPopular?: boolean;
}

const ALL_REPORTS: ReportDef[] = [
  // MANAGEMENT
  {
    id: "management-cockpit",
    name: "Executive BI Cockpit",
    description: "High-level management summary with KPI cards, sales/expense trends, and period comparisons.",
    category: "MANAGEMENT",
    icon: Sparkles,
    path: "/reports/management",
    badge: "Key Insights",
    isPopular: true,
  },

  // FINANCIAL
  {
    id: "trial-balance",
    name: "Trial Balance",
    description: "Standardized double-entry trial balance with debit/credit balance verification and drill-down.",
    category: "FINANCIAL",
    icon: Scale,
    path: "/reports/financial?tab=trial-balance",
    isPopular: true,
  },
  {
    id: "profit-loss",
    name: "Profit & Loss Statement",
    description: "Revenue, cost of sales, gross profit, operating expenses, and net profit with prior period comparison.",
    category: "FINANCIAL",
    icon: TrendingUp,
    path: "/reports/financial?tab=profit-loss",
    isPopular: true,
  },
  {
    id: "balance-sheet",
    name: "Balance Sheet",
    description: "Assets, Liabilities, and Equity statement with real-time balance integrity verification.",
    category: "FINANCIAL",
    icon: Layers,
    path: "/reports/financial?tab=balance-sheet",
    isPopular: true,
  },
  {
    id: "receivables",
    name: "Accounts Receivable",
    description: "Customer invoice balances, credit/debit notes, receipts, net invoiced, and overdue tracking.",
    category: "FINANCIAL",
    icon: UsersRound,
    path: "/reports/financial?tab=receivables",
  },
  {
    id: "payables",
    name: "Accounts Payable",
    description: "Vendor bills, settled amounts, debit notes, and outstanding obligations.",
    category: "FINANCIAL",
    icon: Truck,
    path: "/reports/financial?tab=payables",
  },
  {
    id: "ageing",
    name: "Ageing Analysis",
    description: "Receivables & payables bucketed into Current, 1-30, 31-60, 61-90, 91-180, and 181+ days.",
    category: "FINANCIAL",
    icon: Clock,
    path: "/reports/financial?tab=ageing",
    isPopular: true,
  },
  {
    id: "sales-analytics",
    name: "Sales Register & Analytics",
    description: "Detailed monthly sales distribution, GST slabs, top customers, and average ticket sizes.",
    category: "FINANCIAL",
    icon: BarChart3,
    path: "/reports/financial?tab=sales-analytics",
  },

  // TAX
  {
    id: "gst-summary",
    name: "GST Compliance Summary",
    description: "Outward taxable supplies, input tax credits (ITC), net payable, and GSTR reconciliation status.",
    category: "TAX",
    icon: ShieldCheck,
    path: "/reports/tax?tab=gst",
    isPopular: true,
  },
  {
    id: "tds-summary",
    name: "TDS Intelligence & Challans",
    description: "Section-wise TDS calculated, deducted, challan deposits, and outstanding liability status.",
    category: "TAX",
    icon: Receipt,
    path: "/reports/tax?tab=tds",
  },
  {
    id: "income-tax-summary",
    name: "Income Tax Computation Summary",
    description: "Transparent breakdown by head of income, chapter VI-A deductions, rebate 87A, and final liability.",
    category: "TAX",
    icon: FileSpreadsheet,
    path: "/reports/tax?tab=income-tax",
  },

  // BANK
  {
    id: "cash-bank",
    name: "Cash & Bank Summary",
    description: "Opening balances, collections, disbursements, and account-wise closing balances with reconciliation state.",
    category: "BANK",
    icon: Landmark,
    path: "/reports/banking?tab=cash-bank",
  },
  {
    id: "bank-recon",
    name: "Bank Reconciliation Register",
    description: "Matched vs unmatched transactions, statement line counts, and outstanding adjustments.",
    category: "BANK",
    icon: FileCheck2,
    path: "/bank/reconciliations",
  },

  // AUDIT
  {
    id: "audit-summary",
    name: "Audit Engagements & Findings",
    description: "Engagements progress, checklist completion rate, critical observations, and review status.",
    category: "AUDIT",
    icon: FileCheck2,
    path: "/reports/audit",
  },

  // COMPLIANCE
  {
    id: "compliance-calendar",
    name: "Compliance Status & Calendar",
    description: "Statutory deadlines, overdue obligations, task distributions by regulatory authority.",
    category: "COMPLIANCE",
    icon: CalendarClock,
    path: "/reports/compliance",
  },
];

export default function ReportCenterPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<string>("ALL");

  const filteredReports = ALL_REPORTS.filter((rep) => {
    const matchesSearch =
      rep.name.toLowerCase().includes(search.toLowerCase()) ||
      rep.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = activeTab === "ALL" || rep.category === activeTab;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Report Center & Business Intelligence
            </h1>
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
              Phase 11
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative, auditable, and drill-down reporting across Accounting, Tax, Banking, and Compliance.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => navigate("/reports/management")}
            className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm flex items-center gap-1.5"
          >
            <Sparkles className="h-4 w-4" />
            Executive Cockpit
          </Button>
        </div>
      </div>

      {/* Controls Bar: Search & Category Filter */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-3 rounded-lg border shadow-xs">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search reports by title or keyword..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9 text-sm"
          />
        </div>

        {/* Categories Tab Buttons */}
        <div className="flex flex-wrap gap-1 w-full sm:w-auto">
          {[
            { id: "ALL", label: "All Reports" },
            { id: "MANAGEMENT", label: "Executive" },
            { id: "FINANCIAL", label: "Financial" },
            { id: "TAX", label: "Tax & GST" },
            { id: "BANK", label: "Banking" },
            { id: "AUDIT", label: "Audit" },
            { id: "COMPLIANCE", label: "Compliance" },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveTab(cat.id)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === cat.id
                  ? "bg-slate-900 text-white shadow-xs"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Reports Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredReports.map((report) => {
          const Icon = report.icon;
          return (
            <Card
              key={report.id}
              className="hover:shadow-md transition-shadow duration-200 flex flex-col justify-between border-slate-200 group"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="h-10 w-10 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex items-center gap-1.5">
                    {report.badge && (
                      <Badge variant="secondary" className="bg-indigo-50 text-indigo-700 text-[10px]">
                        {report.badge}
                      </Badge>
                    )}
                    <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                      {report.category}
                    </span>
                  </div>
                </div>
                <CardTitle className="text-base font-semibold mt-3 text-slate-900 group-hover:text-blue-600 transition-colors">
                  {report.name}
                </CardTitle>
                <CardDescription className="text-xs text-slate-500 line-clamp-2 mt-1">
                  {report.description}
                </CardDescription>
              </CardHeader>

              <CardContent className="pt-0">
                <div className="pt-3 border-t flex items-center justify-between">
                  <span className="text-xs text-slate-400">Auditable & Drill-down</span>
                  <Link
                    to={report.path}
                    className="inline-flex items-center text-xs font-semibold text-blue-600 hover:text-blue-800"
                  >
                    Open Report
                    <ChevronRight className="h-3.5 w-3.5 ml-0.5" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {filteredReports.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg border border-dashed">
          <p className="text-sm text-slate-500">No reports matched your search keyword.</p>
          <Button variant="outline" size="sm" onClick={() => { setSearch(""); setActiveTab("ALL"); }} className="mt-3">
            Reset Filter
          </Button>
        </div>
      )}
    </div>
  );
}
