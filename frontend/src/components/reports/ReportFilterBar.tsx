import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Download,
  Filter,
  RefreshCw,
  FileSpreadsheet,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useExportReport } from "@/hooks/useBiReports";

export interface ReportFilterBarProps {
  companyId: string;
  reportType: string;
  showAsOf?: boolean;
  showDateRange?: boolean;
  showCompare?: boolean;
  onFilterChange?: (filters: {
    date_from?: string;
    date_to?: string;
    as_of?: string;
    compare_previous?: boolean;
  }) => void;
}

export function ReportFilterBar({
  companyId,
  reportType,
  showAsOf = false,
  showDateRange = true,
  showCompare = false,
  onFilterChange,
}: ReportFilterBarProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const exportMutation = useExportReport();

  const [dateFrom, setDateFrom] = useState(searchParams.get("date_from") || "");
  const [dateTo, setDateTo] = useState(searchParams.get("date_to") || "");
  const [asOf, setAsOf] = useState(searchParams.get("as_of") || "");
  const [comparePrevious, setComparePrevious] = useState(
    searchParams.get("compare") === "true"
  );
  const [selectedPeriod, setSelectedPeriod] = useState<string>("CUSTOM");

  // Keep state synced when search params change
  useEffect(() => {
    const fromParam = searchParams.get("date_from") || "";
    const toParam = searchParams.get("date_to") || "";
    const asOfParam = searchParams.get("as_of") || "";
    const compareParam = searchParams.get("compare") === "true";

    setDateFrom(fromParam);
    setDateTo(toParam);
    setAsOf(asOfParam);
    setComparePrevious(compareParam);

    if (onFilterChange) {
      onFilterChange({
        date_from: fromParam || undefined,
        date_to: toParam || undefined,
        as_of: asOfParam || undefined,
        compare_previous: compareParam,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleApply = () => {
    const newParams = new URLSearchParams(searchParams);
    if (showDateRange) {
      if (dateFrom) newParams.set("date_from", dateFrom);
      else newParams.delete("date_from");

      if (dateTo) newParams.set("date_to", dateTo);
      else newParams.delete("date_to");
    }

    if (showAsOf) {
      if (asOf) newParams.set("as_of", asOf);
      else newParams.delete("as_of");
    }

    if (showCompare) {
      if (comparePrevious) newParams.set("compare", "true");
      else newParams.delete("compare");
    }

    setSearchParams(newParams);
  };

  const handleReset = () => {
    setDateFrom("");
    setDateTo("");
    setAsOf("");
    setComparePrevious(false);
    setSelectedPeriod("CUSTOM");

    const newParams = new URLSearchParams(searchParams);
    newParams.delete("date_from");
    newParams.delete("date_to");
    newParams.delete("as_of");
    newParams.delete("compare");
    setSearchParams(newParams);
  };

  const handleQuickPeriod = (preset: string) => {
    setSelectedPeriod(preset);
    const today = new Date();
    const curYear = today.getFullYear();
    const curMonth = today.getMonth(); // 0-indexed

    // In India FY runs April 1 to March 31
    const fyStartYear = curMonth >= 3 ? curYear : curYear - 1;

    let from = "";
    let to = "";

    if (preset === "THIS_FY") {
      from = `${fyStartYear}-04-01`;
      to = `${fyStartYear + 1}-03-31`;
    } else if (preset === "Q1") {
      from = `${fyStartYear}-04-01`;
      to = `${fyStartYear}-06-30`;
    } else if (preset === "Q2") {
      from = `${fyStartYear}-07-01`;
      to = `${fyStartYear}-09-30`;
    } else if (preset === "Q3") {
      from = `${fyStartYear}-10-01`;
      to = `${fyStartYear}-12-31`;
    } else if (preset === "Q4") {
      from = `${fyStartYear + 1}-01-01`;
      to = `${fyStartYear + 1}-03-31`;
    } else if (preset === "LAST_MONTH") {
      const firstDayLastMonth = new Date(curYear, curMonth - 1, 1);
      const lastDayLastMonth = new Date(curYear, curMonth, 0);
      from = firstDayLastMonth.toISOString().split("T")[0];
      to = lastDayLastMonth.toISOString().split("T")[0];
    }

    setDateFrom(from);
    setDateTo(to);
    if (showAsOf) {
      setAsOf(to || today.toISOString().split("T")[0]);
    }

    const newParams = new URLSearchParams(searchParams);
    if (from) newParams.set("date_from", from);
    else newParams.delete("date_from");

    if (to) newParams.set("date_to", to);
    else newParams.delete("date_to");

    if (showAsOf) {
      if (to) newParams.set("as_of", to);
    }

    setSearchParams(newParams);
  };

  const handleExport = (format: "CSV" | "XLSX") => {
    exportMutation.mutate({
      companyId,
      reportType,
      format,
      params: {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        as_of: asOf || undefined,
      },
    });
  };

  return (
    <div className="bg-white border rounded-lg p-4 shadow-sm mb-6 flex flex-wrap items-center justify-between gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center text-sm font-medium text-slate-700">
          <Filter className="h-4 w-4 mr-1 text-slate-500" />
          <span>Filters:</span>
        </div>

        {/* Quick Presets */}
        <div className="inline-flex rounded-md shadow-sm border border-slate-200 p-0.5 bg-slate-50 text-xs">
          {[
            { label: "This FY", key: "THIS_FY" },
            { label: "Q1", key: "Q1" },
            { label: "Q2", key: "Q2" },
            { label: "Q3", key: "Q3" },
            { label: "Q4", key: "Q4" },
            { label: "Last Month", key: "LAST_MONTH" },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => handleQuickPeriod(item.key)}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${
                selectedPeriod === item.key
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Date Pickers */}
        {showDateRange && (
          <div className="flex items-center gap-2 text-xs">
            <div className="flex items-center gap-1">
              <span className="text-slate-500">From:</span>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="h-8 w-32 text-xs"
              />
            </div>
            <div className="flex items-center gap-1">
              <span className="text-slate-500">To:</span>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="h-8 w-32 text-xs"
              />
            </div>
          </div>
        )}

        {showAsOf && (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-slate-500">As Of:</span>
            <Input
              type="date"
              value={asOf}
              onChange={(e) => setAsOf(e.target.value)}
              className="h-8 w-32 text-xs"
            />
          </div>
        )}

        {/* Compare Toggle */}
        {showCompare && (
          <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer ml-1 select-none">
            <input
              type="checkbox"
              checked={comparePrevious}
              onChange={(e) => setComparePrevious(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5"
            />
            <span>Compare Previous</span>
          </label>
        )}

        <Button size="sm" variant="default" onClick={handleApply} className="h-8 text-xs px-3">
          Apply
        </Button>
        <Button size="sm" variant="outline" onClick={handleReset} className="h-8 text-xs px-2.5">
          <RefreshCw className="h-3.5 w-3.5 mr-1" />
          Reset
        </Button>
      </div>

      {/* Export Action */}
      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              size="sm"
              variant="outline"
              disabled={exportMutation.isPending}
              className="h-8 text-xs"
            >
              <Download className="h-3.5 w-3.5 mr-1 text-slate-600" />
              {exportMutation.isPending ? "Exporting..." : "Export"}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => handleExport("CSV")}>
              <FileText className="h-4 w-4 mr-2 text-emerald-600" />
              Download as CSV
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleExport("XLSX")}>
              <FileSpreadsheet className="h-4 w-4 mr-2 text-blue-600" />
              Download as Excel (.xlsx)
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
