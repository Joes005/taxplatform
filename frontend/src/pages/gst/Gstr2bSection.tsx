import { Link } from "react-router-dom";
import { FileJson, UploadCloud } from "lucide-react";

import { useGstr2bRecords } from "@/hooks/useGstr2bRecords";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatMoney } from "@/lib/utils";
import { EmptyTableState } from "@/pages/accounting/LedgersPage";

export function Gstr2bSection({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useGstr2bRecords(companyId, periodId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Records imported from a locally uploaded GSTR-2B file (CSV/XLSX/JSON) — never fetched live
          from the GST portal.
        </p>
        <PermissionGate permission="GSTR2B_IMPORT">
          <Button asChild size="sm">
            <Link to={`/accounting/imports/new?importType=GSTR2B&returnPeriodId=${periodId}`}>
              <UploadCloud className="mr-1.5 h-4 w-4" /> Import GSTR-2B
            </Link>
          </Button>
        </PermissionGate>
      </div>

      {isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : data && data.items.length > 0 ? (
        <div className="rounded-lg border border-border bg-white">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Supplier GSTIN</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Invoice #</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Taxable</TableHead>
                <TableHead className="text-right">Total Tax</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs">{r.supplier_gstin}</TableCell>
                  <TableCell>{r.supplier_name ?? "—"}</TableCell>
                  <TableCell className="font-medium">{r.invoice_number}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(r.invoice_date)}</TableCell>
                  <TableCell>{r.document_type}</TableCell>
                  <TableCell className="text-right">{formatMoney(r.taxable_value)}</TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(r.total_tax)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <EmptyTableState
          icon={FileJson}
          title="No GSTR-2B records imported yet"
          hint="Import a GSTR-2B file for this period to enable reconciliation."
        />
      )}
    </div>
  );
}
