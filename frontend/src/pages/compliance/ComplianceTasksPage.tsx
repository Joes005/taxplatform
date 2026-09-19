import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CalendarClock, Download, Plus } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCompanyUsers } from "@/hooks/useCompanyUsers";
import { useComplianceTasks, useCreateComplianceTask } from "@/hooks/useComplianceTasks";
import { complianceTaskService } from "@/services/complianceTaskService";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ApiError } from "@/lib/api-client";
import { triggerBlobDownload } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type {
  ComplianceCategory,
  ComplianceModule,
  CompliancePriority,
  ComplianceTaskStatus,
} from "@/types/compliance";

const STATUS_VARIANT: Record<ComplianceTaskStatus, "secondary" | "warning" | "success" | "outline" | "destructive"> = {
  PENDING: "outline",
  IN_PROGRESS: "secondary",
  PENDING_REVIEW: "warning",
  COMPLETED: "success",
  VERIFIED: "success",
  OVERDUE: "destructive",
  CANCELLED: "outline",
  LOCKED: "success",
};
const PRIORITY_VARIANT: Record<CompliancePriority, "secondary" | "warning" | "destructive"> = {
  LOW: "secondary",
  MEDIUM: "secondary",
  HIGH: "warning",
  CRITICAL: "destructive",
};

const CATEGORIES: ComplianceCategory[] = ["GST", "TDS", "INCOME_TAX", "AUDIT", "ACCOUNTING", "BANK", "GENERAL", "OTHER"];
const MODULES: ComplianceModule[] = ["GST", "TDS", "INCOME_TAX", "AUDIT", "BANK_RECONCILIATION", "ACCOUNTING", "DOCUMENTS", "GENERAL"];
const PRIORITIES: CompliancePriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const STATUSES: ComplianceTaskStatus[] = ["PENDING", "IN_PROGRESS", "PENDING_REVIEW", "COMPLETED", "VERIFIED", "OVERDUE", "CANCELLED", "LOCKED"];

const schema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  category: z.string().min(1),
  module: z.string().min(1),
  priority: z.string().min(1),
  assigned_to: z.string().optional(),
  reviewer_id: z.string().optional(),
  due_date: z.string().min(1, "Due date is required"),
});
type FormValues = z.infer<typeof schema>;

export default function ComplianceTasksPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  if (!activeCompany) return <EmptyCompanyState icon={CalendarClock} />;
  const companyId = activeCompany.company_id;

  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useComplianceTasks(companyId, {
    status: statusFilter === "all" ? undefined : (statusFilter as ComplianceTaskStatus),
    category: categoryFilter === "all" ? undefined : (categoryFilter as ComplianceCategory),
    search: search || undefined,
  });
  const { data: companyUsers } = useCompanyUsers(companyId);
  const createMutation = useCreateComplianceTask(companyId);
  const [open, setOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const { register, control, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { category: "GENERAL", module: "GENERAL", priority: "MEDIUM" },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      await createMutation.mutateAsync({
        ...values,
        category: values.category as ComplianceCategory,
        module: values.module as ComplianceModule,
        priority: values.priority as CompliancePriority,
      });
      toast({ title: "Compliance task created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      toast({ title: "Failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const download = async (format: "csv" | "xlsx") => {
    setDownloading(true);
    try {
      const { blob, filename } = await complianceTaskService.exportTasks(companyId, format);
      triggerBlobDownload(blob, filename ?? `compliance-tasks.${format}`);
    } catch (err) {
      toast({ title: "Export failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  };

  const userLabel = (userId: string | null) => {
    if (!userId) return "—";
    const match = companyUsers?.items.find((u) => u.user_id === userId);
    return match ? `${match.first_name} ${match.last_name}` : userId.slice(0, 8);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Compliance Tasks</h1>
          <p className="text-sm text-muted-foreground">Search, filter, and track every compliance task.</p>
        </div>
        <div className="flex gap-2">
          <PermissionGate permission="COMPLIANCE_REPORT_EXPORT">
            <Button size="sm" variant="outline" disabled={downloading} onClick={() => download("csv")}>
              <Download className="mr-1.5 h-3.5 w-3.5" /> CSV
            </Button>
          </PermissionGate>
          <PermissionGate permission="COMPLIANCE_TASK_CREATE">
            <Button onClick={() => setOpen(true)}><Plus className="mr-1.5 h-4 w-4" /> New Task</Button>
          </PermissionGate>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Input placeholder="Search tasks…" value={search} onChange={(e) => setSearch(e.target.value)} className="w-56" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-44"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUSES.map((s) => <SelectItem key={s} value={s}>{s.replaceAll("_", " ")}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-44"><SelectValue placeholder="Category" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c.replaceAll("_", " ")}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="p-6"><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Assignee</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>
                    <Link to={`/compliance/tasks/${t.id}`} className="font-medium text-primary hover:underline">{t.title}</Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{t.category.replaceAll("_", " ")}</TableCell>
                  <TableCell><Badge variant={PRIORITY_VARIANT[t.priority]}>{t.priority}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{userLabel(t.assigned_to)}</TableCell>
                  <TableCell className={t.is_overdue ? "font-medium text-destructive" : "text-muted-foreground"}>{t.due_date}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[t.status]}>{t.status.replaceAll("_", " ")}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={CalendarClock} title="No compliance tasks yet" hint="Create one to start tracking." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) reset(); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>New compliance task</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div className="space-y-1.5">
              <Label>Title</Label>
              <Input {...register("title")} />
              {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
            </div>
            <div className="space-y-1.5"><Label>Description</Label><Input {...register("description")} /></div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label>Category</Label>
                <Controller control={control} name="category" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c.replaceAll("_", " ")}</SelectItem>)}</SelectContent>
                  </Select>
                )} />
              </div>
              <div className="space-y-1.5">
                <Label>Module</Label>
                <Controller control={control} name="module" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{MODULES.map((m) => <SelectItem key={m} value={m}>{m.replaceAll("_", " ")}</SelectItem>)}</SelectContent>
                  </Select>
                )} />
              </div>
              <div className="space-y-1.5">
                <Label>Priority</Label>
                <Controller control={control} name="priority" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{PRIORITIES.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
                  </Select>
                )} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Assignee</Label>
                <Controller control={control} name="assigned_to" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue placeholder="Unassigned" /></SelectTrigger>
                    <SelectContent>
                      {(companyUsers?.items ?? []).map((u) => <SelectItem key={u.user_id} value={u.user_id}>{u.first_name} {u.last_name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )} />
              </div>
              <div className="space-y-1.5">
                <Label>Reviewer</Label>
                <Controller control={control} name="reviewer_id" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue placeholder="No reviewer" /></SelectTrigger>
                    <SelectContent>
                      {(companyUsers?.items ?? []).map((u) => <SelectItem key={u.user_id} value={u.user_id}>{u.first_name} {u.last_name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Due date</Label>
              <Input type="date" {...register("due_date")} />
              {errors.due_date && <p className="text-xs text-destructive">{errors.due_date.message}</p>}
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
