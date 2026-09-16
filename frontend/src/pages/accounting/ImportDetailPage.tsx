import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Ban } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCancelImportJob, useImportErrors, useImportJob, useImportPreview } from "@/hooks/useImports";
import { PermissionGate } from "@/components/PermissionGate";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";

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

export default function ImportDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id;

  const { data: job, isLoading } = useImportJob(companyId, jobId);
  const { data: preview } = useImportPreview(companyId, jobId);
  const { data: errors } = useImportErrors(companyId, jobId);
  const cancelMutation = useCancelImportJob(companyId ?? "");
  const [confirmCancelOpen, setConfirmCancelOpen] = useState(false);

  if (isLoading || !job) {
    return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-64 w-full" /></div>;
  }

  const handleCancel = async () => {
    try {
      await cancelMutation.mutateAsync(job.id);
      toast({ title: "Import cancelled", variant: "success" });
    } catch (err) {
      toast({ title: "Could not cancel import", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const canCancel = job.status === "READY" || job.status === "UPLOADED";

  return (
    <div className="max-w-4xl space-y-6">
      <Link to="/accounting/imports" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to imports
      </Link>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{job.import_type} import</h1>
          <Badge variant={STATUS_VARIANT[job.status]}>{job.status.replace(/_/g, " ")}</Badge>
        </div>
        {canCancel && (
          <PermissionGate permission="ACCOUNTING_IMPORT">
            <Button variant="outline" onClick={() => setConfirmCancelOpen(true)}>
              <Ban className="mr-1.5 h-4 w-4" /> Cancel
            </Button>
          </PermissionGate>
        )}
      </div>

      <Card>
        <CardHeader><CardTitle>Summary</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-5 gap-4 text-sm">
          <Field label="Total rows" value={String(job.total_rows)} />
          <Field label="Valid" value={String(job.successful_rows)} />
          <Field label="Errors" value={String(job.failed_rows)} />
          <Field label="Duplicates" value={String(job.duplicate_rows)} />
          <Field label="Uploaded" value={formatDateTime(job.created_at)} />
        </CardContent>
      </Card>

      {preview && preview.items.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Rows</CardTitle></CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow><TableHead>Row</TableHead><TableHead>Status</TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {preview.items.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.row_number}</TableCell>
                    <TableCell>
                      <Badge variant={row.status === "VALID" || row.status === "COMMITTED" ? "success" : row.status === "DUPLICATE" ? "warning" : "destructive"}>
                        {row.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {errors && errors.items.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Errors</CardTitle></CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow><TableHead>Row</TableHead><TableHead>Field</TableHead><TableHead>Error</TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {errors.items.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell>{e.row_number}</TableCell>
                    <TableCell className="text-muted-foreground">{e.field_name ?? "—"}</TableCell>
                    <TableCell className="text-xs">{e.error_message}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <ConfirmDialog
        open={confirmCancelOpen}
        onOpenChange={setConfirmCancelOpen}
        title="Cancel import"
        description="This import job will be marked cancelled and cannot be committed. Already-created records (if any) are not affected."
        confirmLabel="Cancel import"
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
