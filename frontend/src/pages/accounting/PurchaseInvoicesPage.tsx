import { useState } from "react";
import { Link } from "react-router-dom";
import { Receipt as ReceiptIcon, Plus } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { usePurchaseInvoices } from "@/hooks/usePurchaseInvoices";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "./LedgersPage";

const STATUS_VARIANT: Record<string, "secondary" | "success" | "destructive"> = {
  DRAFT: "secondary",
  POSTED: "success",
  CANCELLED: "destructive",
};

export default function PurchaseInvoicesPage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id ?? "";
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = usePurchaseInvoices(
    activeCompany ? { companyId, status: status || undefined, page, pageSize: 20 } : null
  );

  if (!activeCompany) return <EmptyCompanyState icon={ReceiptIcon} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Purchase Invoices</h1>
          <p className="text-sm text-muted-foreground">Bills received from vendors</p>
        </div>
        <PermissionGate permission="PURCHASE_CREATE">
          <Button asChild>
            <Link to="/accounting/purchase-invoices/new">
              <Plus className="mr-1.5 h-4 w-4" /> New Invoice
            </Link>
          </Button>
        </PermissionGate>
      </div>

      <div className="flex items-center gap-3 rounded-lg border border-border bg-white p-4">
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
        >
          <option value="">All statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="POSTED">Posted</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice #</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Grand Total</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((inv) => (
                <TableRow key={inv.id}>
                  <TableCell>
                    <Link to={`/accounting/purchase-invoices/${inv.id}`} className="font-medium text-primary hover:underline">
                      {inv.invoice_number}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(inv.invoice_date)}</TableCell>
                  <TableCell className="font-medium">{formatMoney(inv.grand_total)}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[inv.status]}>{inv.status}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={ReceiptIcon} title="No purchase invoices yet" hint="Record your first purchase to get started." />
        )}
      </div>

      {data && data.pagination.total_pages > 1 && (
        <div className="flex items-center justify-end gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
          <span className="text-xs text-muted-foreground">Page {data.pagination.page} of {data.pagination.total_pages}</span>
          <Button variant="outline" size="sm" disabled={page >= data.pagination.total_pages} onClick={() => setPage((p) => p + 1)}>Next</Button>
        </div>
      )}
    </div>
  );
}
