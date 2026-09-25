import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  AlertOctagon,
  AlertCircle,
  Clock,
  CheckCircle2,
  Filter,
  ArrowRight,
  ShieldCheck,
  RotateCcw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/hooks/useAuth";
import { useActionCenter } from "@/hooks/useDashboard";
import type { ActionCenterItem } from "@/types/dashboard";

const CATEGORIES = [
  { value: "ALL", label: "All Categories" },
  { value: "CRITICAL", label: "Critical" },
  { value: "DUE_SOON", label: "Due Soon" },
  { value: "OVERDUE", label: "Overdue" },
  { value: "REVIEW_REQUIRED", label: "Review Required" },
  { value: "PENDING_APPROVAL", label: "Pending Approval" },
  { value: "RECONCILIATION", label: "Reconciliation" },
  { value: "COMPLIANCE", label: "Compliance" },
  { value: "TAX", label: "Tax" },
  { value: "ACCOUNTING", label: "Accounting" },
];

const SEVERITIES = [
  { value: "ALL", label: "All Severities" },
  { value: "CRITICAL", label: "Critical" },
  { value: "HIGH", label: "High" },
  { value: "MEDIUM", label: "Medium" },
  { value: "LOW", label: "Low" },
  { value: "INFO", label: "Info" },
];

const MODULES = [
  { value: "ALL", label: "All Modules" },
  { value: "GST", label: "GST" },
  { value: "TDS", label: "TDS" },
  { value: "BANK", label: "Bank" },
  { value: "ACCOUNTING", label: "Accounting" },
  { value: "INCOME_TAX", label: "Income Tax" },
  { value: "AUDIT", label: "Audit" },
  { value: "COMPLIANCE", label: "Compliance" },
];

export default function ActionCenterPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { activeCompany } = useAuth();

  const [category, setCategory] = useState<string>(searchParams.get("category") || "ALL");
  const [severity, setSeverity] = useState<string>(searchParams.get("severity") || "ALL");
  const [moduleName, setModuleName] = useState<string>(searchParams.get("module_name") || "ALL");
  const [page, setPage] = useState<number>(1);

  // Sync state when search params change
  useEffect(() => {
    const cat = searchParams.get("category");
    const sev = searchParams.get("severity");
    const mod = searchParams.get("module_name");
    if (cat) setCategory(cat);
    if (sev) setSeverity(sev);
    if (mod) setModuleName(mod);
  }, [searchParams]);

  const updateFilters = (newCat: string, newSev: string, newMod: string) => {
    setCategory(newCat);
    setSeverity(newSev);
    setModuleName(newMod);
    setPage(1);

    const params = new URLSearchParams();
    if (newCat !== "ALL") params.set("category", newCat);
    if (newSev !== "ALL") params.set("severity", newSev);
    if (newMod !== "ALL") params.set("module_name", newMod);
    setSearchParams(params);
  };

  const resetFilters = () => {
    updateFilters("ALL", "ALL", "ALL");
  };

  const { data, isLoading, refetch } = useActionCenter(activeCompany?.company_id, {
    category,
    severity,
    module_name: moduleName,
    page,
    page_size: 20,
  });

  const getSeverityBadge = (sev: ActionCenterItem["severity"]) => {
    switch (sev) {
      case "CRITICAL":
        return (
          <Badge variant="destructive" className="gap-1 text-[10px]">
            <AlertOctagon className="h-3 w-3" /> Critical
          </Badge>
        );
      case "HIGH":
        return (
          <Badge variant="secondary" className="gap-1 text-[10px] text-orange-600 bg-orange-500/10 border-orange-500/20">
            <AlertCircle className="h-3 w-3" /> High
          </Badge>
        );
      case "MEDIUM":
        return (
          <Badge variant="secondary" className="gap-1 text-[10px] text-amber-600 bg-amber-500/10 border-amber-500/20">
            <Clock className="h-3 w-3" /> Medium
          </Badge>
        );
      case "LOW":
      case "INFO":
      default:
        return (
          <Badge variant="outline" className="gap-1 text-[10px] text-blue-600 border-blue-500/20">
            Info
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-primary" /> Action Center
          </h1>
          <p className="text-sm text-muted-foreground">
            Centralized clearinghouse for pending tasks, reconciliation exceptions, and compliance deadlines
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} className="gap-1 text-xs">
            <RotateCcw className="h-3.5 w-3.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <Card className="border-border">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Filter className="h-3.5 w-3.5" /> Filter by:
              </div>

              {/* Category */}
              <Select value={category} onValueChange={(val) => updateFilters(val, severity, moduleName)}>
                <SelectTrigger className="h-8 w-44 text-xs">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c.value} value={c.value} className="text-xs">
                      {c.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Severity */}
              <Select value={severity} onValueChange={(val) => updateFilters(category, val, moduleName)}>
                <SelectTrigger className="h-8 w-36 text-xs">
                  <SelectValue placeholder="Severity" />
                </SelectTrigger>
                <SelectContent>
                  {SEVERITIES.map((s) => (
                    <SelectItem key={s.value} value={s.value} className="text-xs">
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Module */}
              <Select value={moduleName} onValueChange={(val) => updateFilters(category, severity, val)}>
                <SelectTrigger className="h-8 w-36 text-xs">
                  <SelectValue placeholder="Module" />
                </SelectTrigger>
                <SelectContent>
                  {MODULES.map((m) => (
                    <SelectItem key={m.value} value={m.value} className="text-xs">
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {(category !== "ALL" || severity !== "ALL" || moduleName !== "ALL") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={resetFilters}
                className="h-8 text-xs text-muted-foreground hover:text-foreground"
              >
                Clear Filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action Items List */}
      <Card className="border-border">
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base font-semibold">
                Action Items ({data?.pagination.total ?? 0})
              </CardTitle>
              <CardDescription className="text-xs">
                Items requiring user action or review across active company workflows
              </CardDescription>
            </div>
            {data && data.pagination.total_pages > 1 && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                Page {page} of {data.pagination.total_pages}
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {!activeCompany ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              Please select an active company to review actionable tasks.
            </div>
          ) : isLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-16 w-full rounded-lg" />
              <Skeleton className="h-16 w-full rounded-lg" />
              <Skeleton className="h-16 w-full rounded-lg" />
            </div>
          ) : data?.items.length === 0 ? (
            <div className="p-12 text-center flex flex-col items-center justify-center">
              <CheckCircle2 className="h-10 w-10 text-emerald-500 mb-3" />
              <h3 className="text-base font-semibold text-foreground">Zero Pending Action Items</h3>
              <p className="text-xs text-muted-foreground max-w-sm mt-1">
                There are no open action items matching your current filters. All GST returns, TDS challans, bank entries, and compliance tasks are up to date!
              </p>
              {(category !== "ALL" || severity !== "ALL" || moduleName !== "ALL") && (
                <Button variant="outline" size="sm" onClick={resetFilters} className="mt-4 text-xs">
                  Reset Filters
                </Button>
              )}
            </div>
          ) : (
            <div className="divide-y divide-border">
              {data?.items.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 gap-3 hover:bg-muted/30 transition-colors"
                >
                  <div className="space-y-1.5 max-w-3xl">
                    <div className="flex flex-wrap items-center gap-2">
                      {getSeverityBadge(item.severity)}
                      <Badge variant="outline" className="text-[10px] font-mono">
                        {item.module}
                      </Badge>
                      <Badge variant="secondary" className="text-[10px]">
                        {item.category.replace(/_/g, " ")}
                      </Badge>
                      <span className="text-sm font-semibold text-foreground">
                        {item.title}
                      </span>
                    </div>

                    <p className="text-xs text-muted-foreground">
                      {item.description}
                    </p>

                    <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground pt-1">
                      {item.due_date && (
                        <span className="flex items-center gap-1 font-medium text-foreground">
                          <Clock className="h-3 w-3 text-amber-500" /> Due: {item.due_date}
                        </span>
                      )}
                      {item.created_date && (
                        <span>Detected: {item.created_date}</span>
                      )}
                      {item.source_reference && (
                        <span className="font-mono bg-muted px-1.5 py-0.5 rounded text-[10px]">
                          Ref: {item.source_reference}
                        </span>
                      )}
                      {item.responsible_roles.length > 0 && (
                        <span>Roles: {item.responsible_roles.join(", ")}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                    <Button
                      size="sm"
                      onClick={() => navigate(item.target_url)}
                      className="gap-1.5 text-xs font-semibold"
                    >
                      Resolve Task <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {data && data.pagination.total_pages > 1 && (
            <div className="flex items-center justify-between p-4 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="text-xs"
              >
                Previous
              </Button>
              <span className="text-xs text-muted-foreground">
                Page {page} of {data.pagination.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.pagination.total_pages}
                onClick={() => setPage(page + 1)}
                className="text-xs"
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
