import { useState } from "react";
import { AlertTriangle, Download, FileWarning } from "lucide-react";

import {
  useGstr1B2B,
  useGstr1B2CLarge,
  useGstr1B2COthers,
  useGstr1CreditNotes,
  useGstr1DebitNotes,
  useGstr1Documents,
  useGstr1HSN,
  useGstr1Validation,
} from "@/hooks/useGstr1";
import { useToast } from "@/hooks/useToast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatMoney, triggerBlobDownload } from "@/lib/utils";
import { EmptyTableState } from "@/pages/accounting/LedgersPage";
import { gstReturnPeriodService } from "@/services/gstReturnPeriodService";
import type { GSTR1NoteRow } from "@/types/gst";

const SEVERITY_VARIANT: Record<string, "destructive" | "warning" | "secondary"> = {
  ERROR: "destructive",
  WARNING: "warning",
  INFO: "secondary",
};

export function Gstr1Section({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { toast } = useToast();
  const [downloading, setDownloading] = useState(false);

  const handleExport = async (format: "csv" | "xlsx") => {
    setDownloading(true);
    try {
      const { blob, filename } = await gstReturnPeriodService.exportGstr1(companyId, periodId, format);
      triggerBlobDownload(blob, filename ?? `gstr1-preparation.${format}`);
      toast({ title: `GSTR-1 exported (${format.toUpperCase()})`, variant: "success" });
    } catch {
      toast({ title: "Failed to export GSTR-1", variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          GSTR-1 return preparation data across outward supplies, credit/debit notes, HSN summaries, and validation rules.
        </p>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            variant="outline"
            disabled={downloading}
            onClick={() => handleExport("csv")}
            className="gap-1.5"
          >
            <Download className="h-3.5 w-3.5" /> Export CSV
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={downloading}
            onClick={() => handleExport("xlsx")}
            className="gap-1.5"
          >
            <Download className="h-3.5 w-3.5" /> Export Excel
          </Button>
        </div>
      </div>

      <Tabs defaultValue="b2b">
        <TabsList className="flex-wrap h-auto">
          <TabsTrigger value="b2b">B2B</TabsTrigger>
          <TabsTrigger value="b2c-large">B2C Large</TabsTrigger>
          <TabsTrigger value="b2c-others">B2C Others</TabsTrigger>
          <TabsTrigger value="exports">Exports</TabsTrigger>
          <TabsTrigger value="credit-notes">Credit Notes</TabsTrigger>
          <TabsTrigger value="debit-notes">Debit Notes</TabsTrigger>
          <TabsTrigger value="hsn">HSN Summary</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
        </TabsList>

      <TabsContent value="b2b"><B2BTab companyId={companyId} periodId={periodId} /></TabsContent>
      <TabsContent value="b2c-large"><B2CLargeTab companyId={companyId} periodId={periodId} /></TabsContent>
      <TabsContent value="b2c-others"><B2COthersTab companyId={companyId} periodId={periodId} /></TabsContent>
      <TabsContent value="exports">
        <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
          Export detection needs a per-customer export/SEZ indicator that isn't captured yet — no export
          rows are auto-classified in this phase. Add exports here manually in your CA workflow.
        </div>
      </TabsContent>
      <TabsContent value="credit-notes"><NotesTab companyId={companyId} periodId={periodId} kind="credit" /></TabsContent>
      <TabsContent value="debit-notes"><NotesTab companyId={companyId} periodId={periodId} kind="debit" /></TabsContent>
      <TabsContent value="hsn"><HsnTab companyId={companyId} periodId={periodId} /></TabsContent>
      <TabsContent value="documents"><DocumentsTab companyId={companyId} periodId={periodId} /></TabsContent>
      <TabsContent value="validation"><ValidationTab companyId={companyId} periodId={periodId} /></TabsContent>
    </Tabs>
  </div>
);
}

function B2BTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useGstr1B2B(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.length === 0) return <EmptyTableState icon={FileWarning} title="No B2B invoices" />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Invoice #</TableHead>
          <TableHead>Date</TableHead>
          <TableHead>Recipient GSTIN</TableHead>
          <TableHead>Place of Supply</TableHead>
          <TableHead className="text-right">Taxable</TableHead>
          <TableHead className="text-right">CGST</TableHead>
          <TableHead className="text-right">SGST</TableHead>
          <TableHead className="text-right">IGST</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.sales_invoice_id}>
            <TableCell className="font-medium">{row.invoice_number}</TableCell>
            <TableCell className="text-muted-foreground">{formatDate(row.invoice_date)}</TableCell>
            <TableCell className="font-mono text-xs">{row.recipient_gstin}</TableCell>
            <TableCell>{row.place_of_supply_state_code ?? "—"}</TableCell>
            <TableCell className="text-right">{formatMoney(row.taxable_value)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.cgst_amount)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.sgst_amount)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.igst_amount)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function B2CLargeTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useGstr1B2CLarge(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.length === 0) return <EmptyTableState icon={FileWarning} title="No B2C Large invoices" hint="Inter-state invoices to unregistered persons over ₹2.5 lakh." />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Invoice #</TableHead>
          <TableHead>Date</TableHead>
          <TableHead>Place of Supply</TableHead>
          <TableHead className="text-right">Taxable</TableHead>
          <TableHead className="text-right">IGST</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.sales_invoice_id}>
            <TableCell className="font-medium">{row.invoice_number}</TableCell>
            <TableCell className="text-muted-foreground">{formatDate(row.invoice_date)}</TableCell>
            <TableCell>{row.place_of_supply_state_code ?? "—"}</TableCell>
            <TableCell className="text-right">{formatMoney(row.taxable_value)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.igst_amount)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function B2COthersTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useGstr1B2COthers(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.length === 0) return <EmptyTableState icon={FileWarning} title="No B2C transactions" />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Place of Supply</TableHead>
          <TableHead>Rate</TableHead>
          <TableHead className="text-right">Invoices</TableHead>
          <TableHead className="text-right">Taxable</TableHead>
          <TableHead className="text-right">CGST</TableHead>
          <TableHead className="text-right">SGST</TableHead>
          <TableHead className="text-right">IGST</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row, i) => (
          <TableRow key={i}>
            <TableCell>{row.place_of_supply_state_code ?? "—"}</TableCell>
            <TableCell>{row.tax_rate}%</TableCell>
            <TableCell className="text-right">{row.invoice_count}</TableCell>
            <TableCell className="text-right">{formatMoney(row.taxable_value)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.cgst_amount)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.sgst_amount)}</TableCell>
            <TableCell className="text-right">{formatMoney(row.igst_amount)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function NotesTab({ companyId, periodId, kind }: { companyId: string; periodId: string; kind: "credit" | "debit" }) {
  const creditQuery = useGstr1CreditNotes(kind === "credit" ? companyId : undefined, periodId);
  const debitQuery = useGstr1DebitNotes(kind === "debit" ? companyId : undefined, periodId);
  const { data, isLoading } = kind === "credit" ? creditQuery : debitQuery;

  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.length === 0) return <EmptyTableState icon={FileWarning} title={`No ${kind} notes`} />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Note #</TableHead>
          <TableHead>Date</TableHead>
          <TableHead>Against Invoice</TableHead>
          <TableHead>Recipient</TableHead>
          <TableHead className="text-right">Taxable</TableHead>
          <TableHead className="text-right">Tax</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row: GSTR1NoteRow) => (
          <TableRow key={row.note_id}>
            <TableCell className="font-medium">{row.note_number}</TableCell>
            <TableCell className="text-muted-foreground">{formatDate(row.note_date)}</TableCell>
            <TableCell>{row.reference_invoice_number ?? "—"}</TableCell>
            <TableCell>{row.recipient_name ?? "—"}</TableCell>
            <TableCell className="text-right">{formatMoney(row.taxable_value)}</TableCell>
            <TableCell className="text-right">
              {formatMoney(
                (parseFloat(row.cgst_amount) + parseFloat(row.sgst_amount) + parseFloat(row.igst_amount)).toFixed(2)
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function HsnTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useGstr1HSN(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.length === 0) return <EmptyTableState icon={FileWarning} title="No HSN/SAC data" />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>HSN/SAC</TableHead>
          <TableHead>Description</TableHead>
          <TableHead>Rate</TableHead>
          <TableHead className="text-right">Qty</TableHead>
          <TableHead className="text-right">Taxable</TableHead>
          <TableHead className="text-right">Total</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row, i) => (
          <TableRow key={i}>
            <TableCell className="font-medium">
              {row.hsn_sac ?? <Badge variant="warning">Missing</Badge>}
            </TableCell>
            <TableCell className="text-muted-foreground">{row.description ?? "—"}</TableCell>
            <TableCell>{row.tax_rate}%</TableCell>
            <TableCell className="text-right">{row.quantity}</TableCell>
            <TableCell className="text-right">{formatMoney(row.taxable_value)}</TableCell>
            <TableCell className="text-right font-medium">{formatMoney(row.total_value)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function DocumentsTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useGstr1Documents(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.length === 0) return <EmptyTableState icon={FileWarning} title="No documents" />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Document Type</TableHead>
          <TableHead className="text-right">Total</TableHead>
          <TableHead className="text-right">Cancelled</TableHead>
          <TableHead className="text-right">Net</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.document_type}>
            <TableCell className="font-medium">{row.document_type}</TableCell>
            <TableCell className="text-right">{row.total_count}</TableCell>
            <TableCell className="text-right text-muted-foreground">{row.cancelled_count}</TableCell>
            <TableCell className="text-right font-medium">{row.net_count}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ValidationTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useGstr1Validation(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data || data.findings.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border bg-white p-6 text-sm text-success">
        No validation issues found.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        <Badge variant="destructive">{data.error_count} errors</Badge>
        <Badge variant="warning">{data.warning_count} warnings</Badge>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Severity</TableHead>
            <TableHead>Code</TableHead>
            <TableHead>Entity</TableHead>
            <TableHead>Message</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.findings.map((f, i) => (
            <TableRow key={i}>
              <TableCell><Badge variant={SEVERITY_VARIANT[f.severity]}>{f.severity}</Badge></TableCell>
              <TableCell className="font-mono text-xs">{f.code}</TableCell>
              <TableCell className="text-xs text-muted-foreground">{f.entity} · {f.entity_id.slice(0, 8)}</TableCell>
              <TableCell className="flex items-start gap-1.5 text-sm">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                {f.message}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
