import { useState } from "react";
import { BarChart3, Download } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import {
  useCustomerOutstanding,
  usePurchaseSummary,
  useSalesSummary,
  useTrialBalance,
  useVendorOutstanding,
} from "@/hooks/useReports";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMoney, triggerBlobDownload } from "@/lib/utils";
import { reportService } from "@/services/reportService";
import { EmptyCompanyState, EmptyTableState } from "./LedgersPage";
import type { PartyOutstanding, SalesPurchaseSummary } from "@/types/accounting";

export default function ReportsPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={BarChart3} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground">Sales, purchases, outstanding balances, and trial balance</p>
      </div>
      <Tabs defaultValue="sales">
        <TabsList>
          <TabsTrigger value="sales">Sales Summary</TabsTrigger>
          <TabsTrigger value="purchases">Purchase Summary</TabsTrigger>
          <TabsTrigger value="customer-outstanding">Customer Outstanding</TabsTrigger>
          <TabsTrigger value="vendor-outstanding">Vendor Outstanding</TabsTrigger>
          <TabsTrigger value="trial-balance">Trial Balance</TabsTrigger>
        </TabsList>
        <TabsContent value="sales"><SummaryTab companyId={activeCompany.company_id} kind="sales" /></TabsContent>
        <TabsContent value="purchases"><SummaryTab companyId={activeCompany.company_id} kind="purchases" /></TabsContent>
        <TabsContent value="customer-outstanding"><OutstandingTab companyId={activeCompany.company_id} kind="customer" /></TabsContent>
        <TabsContent value="vendor-outstanding"><OutstandingTab companyId={activeCompany.company_id} kind="vendor" /></TabsContent>
        <TabsContent value="trial-balance"><TrialBalanceTab companyId={activeCompany.company_id} /></TabsContent>
      </Tabs>
    </div>
  );
}

function DateRangeFilters({
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
}: {
  dateFrom: string;
  dateTo: string;
  onDateFromChange: (v: string) => void;
  onDateToChange: (v: string) => void;
}) {
  return (
    <div className="flex items-end gap-3">
      <div className="space-y-1.5">
        <Label>From</Label>
        <Input type="date" value={dateFrom} onChange={(e) => onDateFromChange(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label>To</Label>
        <Input type="date" value={dateTo} onChange={(e) => onDateToChange(e.target.value)} />
      </div>
    </div>
  );
}

function SummaryTab({ companyId, kind }: { companyId: string; kind: "sales" | "purchases" }) {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [downloading, setDownloading] = useState(false);
  const { toast } = useToast();
  const salesQuery = useSalesSummary(kind === "sales" ? companyId : undefined, dateFrom || undefined, dateTo || undefined);
  const purchaseQuery = usePurchaseSummary(kind === "purchases" ? companyId : undefined, dateFrom || undefined, dateTo || undefined);
  const { data, isLoading } = kind === "sales" ? salesQuery : purchaseQuery;

  const handleExport = async (format: "csv" | "xlsx") => {
    setDownloading(true);
    try {
      const res =
        kind === "sales"
          ? await reportService.exportSalesRegister(companyId, format, dateFrom || undefined, dateTo || undefined)
          : await reportService.exportPurchaseRegister(companyId, format, dateFrom || undefined, dateTo || undefined);
      triggerBlobDownload(res.blob, res.filename ?? `${kind}-register.${format}`);
      toast({
        title: `${kind === "sales" ? "Sales" : "Purchase"} register exported (${format.toUpperCase()})`,
        variant: "success",
      });
    } catch {
      toast({ title: "Export failed", variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <DateRangeFilters dateFrom={dateFrom} dateTo={dateTo} onDateFromChange={setDateFrom} onDateToChange={setDateTo} />
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={downloading || isLoading || !data || data.invoice_count === 0}
            onClick={() => handleExport("csv")}
            className="gap-1.5"
          >
            <Download className="h-3.5 w-3.5" /> Export CSV
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={downloading || isLoading || !data || data.invoice_count === 0}
            onClick={() => handleExport("xlsx")}
            className="gap-1.5"
          >
            <Download className="h-3.5 w-3.5" /> Export Excel
          </Button>
        </div>
      </div>
      {isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : data ? (
        <SummaryCards data={data} />
      ) : (
        <EmptyTableState icon={BarChart3} title="No data for this range" />
      )}
    </div>
  );
}

function SummaryCards({ data }: { data: SalesPurchaseSummary }) {
  const rows: [string, string][] = [
    ["Invoices", String(data.invoice_count)],
    ["Taxable Amount", formatMoney(data.taxable_amount)],
    ["CGST", formatMoney(data.cgst_amount)],
    ["SGST", formatMoney(data.sgst_amount)],
    ["IGST", formatMoney(data.igst_amount)],
    ["Cess", formatMoney(data.cess_amount)],
    ["Total Tax", formatMoney(data.total_tax)],
    ["Grand Total", formatMoney(data.grand_total)],
  ];
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {rows.map(([label, value]) => (
        <Card key={label}>
          <CardContent className="pt-6">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
            <p className="mt-1 text-lg font-semibold">{value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function OutstandingTab({ companyId, kind }: { companyId: string; kind: "customer" | "vendor" }) {
  const customerQuery = useCustomerOutstanding(kind === "customer" ? companyId : undefined);
  const vendorQuery = useVendorOutstanding(kind === "vendor" ? companyId : undefined);
  const { data, isLoading } = kind === "customer" ? customerQuery : vendorQuery;

  return (
    <Card>
      <CardHeader><CardTitle>{kind === "customer" ? "Customer" : "Vendor"} outstanding</CardTitle></CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-6"><Skeleton className="h-10 w-full" /></div>
        ) : data && data.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{kind === "customer" ? "Customer" : "Vendor"}</TableHead>
                <TableHead className="text-right">Invoiced</TableHead>
                <TableHead className="text-right">Settled</TableHead>
                <TableHead className="text-right">Outstanding</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((row: PartyOutstanding) => (
                <TableRow key={row.party_id}>
                  <TableCell className="font-medium">{row.party_name}</TableCell>
                  <TableCell className="text-right">{formatMoney(row.invoiced_total)}</TableCell>
                  <TableCell className="text-right text-muted-foreground">{formatMoney(row.settled_total)}</TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(row.outstanding)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={BarChart3} title="Nothing outstanding" />
        )}
      </CardContent>
    </Card>
  );
}

function TrialBalanceTab({ companyId }: { companyId: string }) {
  const [asOf, setAsOf] = useState("");
  const [downloading, setDownloading] = useState(false);
  const { toast } = useToast();
  const { data, isLoading } = useTrialBalance(companyId, asOf || undefined);

  const handleExport = async (format: "csv" | "xlsx") => {
    setDownloading(true);
    try {
      const res = await reportService.exportTrialBalance(companyId, format, asOf || undefined);
      triggerBlobDownload(res.blob, res.filename ?? `trial-balance.${format}`);
      toast({ title: `Trial balance exported (${format.toUpperCase()})`, variant: "success" });
    } catch {
      toast({ title: "Export failed", variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div className="flex items-end gap-3">
          <div className="space-y-1.5">
            <Label>As of</Label>
            <Input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
          </div>
          {data && (
            <Badge variant={data.is_balanced ? "success" : "destructive"}>
              {data.is_balanced ? "Balanced" : "Not balanced"}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={downloading || isLoading || !data || data.lines.length === 0}
            onClick={() => handleExport("csv")}
            className="gap-1.5"
          >
            <Download className="h-3.5 w-3.5" /> Export CSV
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={downloading || isLoading || !data || data.lines.length === 0}
            onClick={() => handleExport("xlsx")}
            className="gap-1.5"
          >
            <Download className="h-3.5 w-3.5" /> Export Excel
          </Button>
        </div>
      </div>
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6"><Skeleton className="h-10 w-full" /></div>
          ) : data && data.lines.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ledger</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Debit</TableHead>
                    <TableHead className="text-right">Credit</TableHead>
                    <TableHead className="text-right">Balance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.lines.map((line) => (
                    <TableRow key={line.ledger_id}>
                      <TableCell className="font-medium">{line.ledger_name}</TableCell>
                      <TableCell className="text-muted-foreground">{line.ledger_type}</TableCell>
                      <TableCell className="text-right">{formatMoney(line.debit)}</TableCell>
                      <TableCell className="text-right">{formatMoney(line.credit)}</TableCell>
                      <TableCell className="text-right font-medium">
                        {formatMoney(line.balance)} {line.balance_type}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="flex justify-end gap-6 border-t border-border px-4 py-3 text-sm font-semibold">
                <span>Total Debit: {formatMoney(data.total_debit)}</span>
                <span>Total Credit: {formatMoney(data.total_credit)}</span>
              </div>
            </>
          ) : (
            <EmptyTableState icon={BarChart3} title="No ledger balances yet" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
