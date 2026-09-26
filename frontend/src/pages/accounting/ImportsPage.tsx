import { Link } from "react-router-dom";
import { FileSpreadsheet, Plus, UploadCloud } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useImportJobs } from "@/hooks/useImports";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "./LedgersPage";

const STATUS_VARIANT: Record<string, "secondary" | "success" | "destructive" | "warning" | "outline"> = {
  UPLOADED: "outline",
  PARSING: "warning",
  VALIDATING: "warning",
  READY: "outline",
  PROCESSING: "warning",
  COMPLETED: "success",
  COMPLETED_WITH_ERRORS: "warning",
  FAILED: "destructive",
  CANCELLED: "secondary",
};

export default function ImportsPage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id ?? "";
  const { data, isLoading } = useImportJobs(companyId);

  if (!activeCompany) return <EmptyCompanyState icon={UploadCloud} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Imports</h1>
          <p className="text-sm text-muted-foreground">Bring in data from Tally exports, Excel, or CSV files</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/accounting/tally">
              <FileSpreadsheet className="mr-1.5 h-4 w-4 text-primary" /> Tally Bridge
            </Link>
          </Button>
          <PermissionGate permission="ACCOUNTING_IMPORT">
            <Button asChild>
              <Link to="/accounting/imports/new">
                <Plus className="mr-1.5 h-4 w-4" /> New Import
              </Link>
            </Button>
          </PermissionGate>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Uploaded</TableHead>
                <TableHead>Rows</TableHead>
                <TableHead>Valid</TableHead>
                <TableHead>Errors</TableHead>
                <TableHead>Duplicates</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((job) => (
                <TableRow key={job.id}>
                  <TableCell>
                    <Link to={`/accounting/imports/${job.id}`} className="font-medium text-primary hover:underline">
                      {job.import_type}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatDateTime(job.created_at)}</TableCell>
                  <TableCell>{job.total_rows}</TableCell>
                  <TableCell className="text-success">{job.successful_rows}</TableCell>
                  <TableCell className="text-destructive">{job.failed_rows}</TableCell>
                  <TableCell className="text-warning">{job.duplicate_rows}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[job.status]}>{job.status.replace(/_/g, " ")}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={UploadCloud} title="No imports yet" hint="Upload a CSV, Excel, or Tally export to get started." />
        )}
      </div>
    </div>
  );
}
