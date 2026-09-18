import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ClipboardCheck, Plus } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import { useAuditEngagements, useCreateAuditEngagement } from "@/hooks/useAuditEngagements";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError } from "@/lib/api-client";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { AuditEngagementStatus, AuditEngagementType } from "@/types/audit";

const STATUS_VARIANT: Record<AuditEngagementStatus, "secondary" | "warning" | "success" | "outline"> = {
  DRAFT: "outline",
  OPEN: "secondary",
  ASSIGNED: "secondary",
  IN_REVIEW: "warning",
  PENDING_CLIENT_ACTION: "warning",
  PENDING_AUDITOR_REVIEW: "warning",
  APPROVED: "success",
  SIGNED_OFF: "success",
  CLOSED: "success",
  CANCELLED: "outline",
};

const ENGAGEMENT_TYPES: AuditEngagementType[] = [
  "INTERNAL_REVIEW",
  "TAX_COMPLIANCE_REVIEW",
  "FINANCIAL_REVIEW",
  "BOOKS_REVIEW",
  "PRE_AUDIT_REVIEW",
  "GENERAL_AUDIT",
  "OTHER",
];

const schema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  financial_year_id: z.string().min(1, "Select a financial year"),
  period_start: z.string().min(1, "Start date is required"),
  period_end: z.string().min(1, "End date is required"),
  engagement_type: z.string().min(1),
});
type FormValues = z.infer<typeof schema>;

export default function AuditEngagementsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";
  const { data, isLoading } = useAuditEngagements(companyId);
  const { data: financialYears } = useFinancialYears(companyId);
  const createMutation = useCreateAuditEngagement(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { engagement_type: "INTERNAL_REVIEW" } });

  if (!activeCompany) return <EmptyCompanyState icon={ClipboardCheck} />;

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({
        ...values,
        engagement_type: values.engagement_type as AuditEngagementType,
      });
      toast({ title: "Engagement created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Audit Engagements</h1>
          <p className="text-sm text-muted-foreground">Create a review workspace for a financial year or period.</p>
        </div>
        <PermissionGate permission="AUDIT_ENGAGEMENT_CREATE">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New Engagement
          </Button>
        </PermissionGate>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Period</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((e) => (
                <TableRow key={e.id}>
                  <TableCell className="font-medium">
                    <Link to={`/audits/engagements/${e.id}`} className="text-primary hover:underline">
                      {e.engagement_code}
                    </Link>
                  </TableCell>
                  <TableCell>{e.title}</TableCell>
                  <TableCell className="text-muted-foreground">{e.period_start} to {e.period_end}</TableCell>
                  <TableCell className="text-muted-foreground">{e.engagement_type.replaceAll("_", " ")}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[e.status]}>{e.status}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={ClipboardCheck} title="No engagements yet" hint="Create one to start a review." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>New audit engagement</DialogTitle>
            <DialogDescription>
              An internal review workspace — not a statutory audit filing or certification.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label htmlFor="eng-title">Title</Label>
              <Input id="eng-title" {...register("title")} />
              {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="eng-description">Description</Label>
              <Textarea id="eng-description" rows={2} {...register("description")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="eng-fy">Financial year</Label>
              <Controller
                control={control}
                name="financial_year_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="eng-fy"><SelectValue placeholder="Select financial year" /></SelectTrigger>
                    <SelectContent>
                      {(financialYears?.items ?? []).map((fy) => (
                        <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.financial_year_id && <p className="text-xs text-destructive">{errors.financial_year_id.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="eng-start">Period start</Label>
                <Input id="eng-start" type="date" {...register("period_start")} />
                {errors.period_start && <p className="text-xs text-destructive">{errors.period_start.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="eng-end">Period end</Label>
                <Input id="eng-end" type="date" {...register("period_end")} />
                {errors.period_end && <p className="text-xs text-destructive">{errors.period_end.message}</p>}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="eng-type">Engagement type</Label>
              <Controller
                control={control}
                name="engagement_type"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="eng-type"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {ENGAGEMENT_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>{t.replaceAll("_", " ")}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Creating…" : "Create"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
