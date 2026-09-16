import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, XCircle } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCancelPurchaseInvoice, usePostPurchaseInvoice, usePurchaseInvoice } from "@/hooks/usePurchaseInvoices";
import { PermissionGate } from "@/components/PermissionGate";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatMoney } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";

const STATUS_VARIANT: Record<string, "secondary" | "success" | "destructive"> = {
  DRAFT: "secondary",
  POSTED: "success",
  CANCELLED: "destructive",
};

export default function PurchaseInvoiceDetailPage() {
  const { invoiceId } = useParams<{ invoiceId: string }>();
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id;
  const { data: invoice, isLoading } = usePurchaseInvoice(companyId, invoiceId);
  const postMutation = usePostPurchaseInvoice(companyId ?? "");
  const cancelMutation = useCancelPurchaseInvoice(companyId ?? "");
  const [confirmCancelOpen, setConfirmCancelOpen] = useState(false);

  if (isLoading || !invoice) {
    return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-64 w-full" /></div>;
  }

  const handlePost = async () => {
    try {
      await postMutation.mutateAsync(invoice.id);
      toast({ title: "Invoice posted", variant: "success" });
    } catch (err) {
      toast({ title: "Could not post invoice", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const handleCancel = async () => {
    await cancelMutation.mutateAsync(invoice.id);
    toast({ title: "Invoice cancelled", variant: "success" });
  };

  return (
    <div className="max-w-4xl space-y-6">
      <Link to="/accounting/purchase-invoices" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to purchase invoices
      </Link>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{invoice.invoice_number}</h1>
          <Badge variant={STATUS_VARIANT[invoice.status]}>{invoice.status}</Badge>
        </div>
        <div className="flex gap-2">
          {invoice.status === "DRAFT" && (
            <PermissionGate permission="PURCHASE_POST">
              <Button onClick={handlePost}>
                <CheckCircle2 className="mr-1.5 h-4 w-4" /> Post
              </Button>
            </PermissionGate>
          )}
          {invoice.status !== "CANCELLED" && (
            <PermissionGate permission="PURCHASE_CANCEL">
              <Button variant="outline" onClick={() => setConfirmCancelOpen(true)}>
                <XCircle className="mr-1.5 h-4 w-4" /> Cancel
              </Button>
            </PermissionGate>
          )}
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle>Details</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-3 gap-4 text-sm">
          <Field label="Invoice Date" value={formatDate(invoice.invoice_date)} />
          <Field label="Supplier Invoice #" value={invoice.supplier_invoice_number ?? "—"} />
          <Field label="Source" value={invoice.source} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Line items</CardTitle></CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Description</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Rate</TableHead>
                <TableHead>Taxable</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoice.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.description ?? "—"}</TableCell>
                  <TableCell>{item.quantity}</TableCell>
                  <TableCell>{formatMoney(item.unit_price)}</TableCell>
                  <TableCell>{formatMoney(item.taxable_value)}</TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(item.total_amount)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-2 pt-6 text-sm">
          <SummaryRow label="Taxable Amount" value={formatMoney(invoice.taxable_amount)} />
          <SummaryRow label="CGST" value={formatMoney(invoice.cgst_amount)} />
          <SummaryRow label="SGST" value={formatMoney(invoice.sgst_amount)} />
          <SummaryRow label="IGST" value={formatMoney(invoice.igst_amount)} />
          <div className="flex justify-between border-t border-border pt-2 text-base font-semibold">
            <span>Grand Total</span>
            <span>{formatMoney(invoice.grand_total)}</span>
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmCancelOpen}
        onOpenChange={setConfirmCancelOpen}
        title="Cancel invoice"
        description={`"${invoice.invoice_number}" will be marked cancelled. This is a terminal state — it cannot be reopened.`}
        confirmLabel="Cancel invoice"
        onConfirm={handleCancel}
      />
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1">{value}</dd>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-muted-foreground">
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
