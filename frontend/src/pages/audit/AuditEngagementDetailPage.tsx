import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, ClipboardCheck, Download, Plus } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCompanyUsers } from "@/hooks/useCompanyUsers";
import {
  useApproveAuditEngagement,
  useAssignAuditEngagementUser,
  useAuditAssignments,
  useAuditEngagement,
  useAuditSignOffs,
  useCancelAuditEngagement,
  useCloseAuditEngagement,
  useCreateAuditSignOff,
  useLockAuditEngagement,
  useMarkAuditEngagementSignedOff,
  useOpenAuditEngagement,
  useRequestAuditClientAction,
  useResumeAuditEngagementReview,
  useReturnAuditEngagementForChanges,
  useStartAuditEngagementReview,
  useSubmitAuditEngagementForReview,
  useUnassignAuditEngagementUser,
} from "@/hooks/useAuditEngagements";
import { useAuditEngagementProgress } from "@/hooks/useAuditReports";
import { useAuditChecklist, useUpdateAuditChecklistItem } from "@/hooks/useAuditChecklist";
import { useAuditFindingsForEngagement, useCreateAuditFinding } from "@/hooks/useAuditFindings";
import { useAuditReviews, useCompleteAuditReview, useStartAuditReview } from "@/hooks/useAuditReviews";
import { auditReportService } from "@/services/auditReportService";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError } from "@/lib/api-client";
import { triggerBlobDownload } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type {
  AuditAssignmentRole,
  AuditChecklistItemStatus,
  AuditEngagementStatus,
  AuditFindingCategory,
  AuditFindingSeverity,
} from "@/types/audit";

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

const SEVERITY_VARIANT: Record<AuditFindingSeverity, "secondary" | "warning" | "destructive"> = {
  LOW: "secondary",
  MEDIUM: "secondary",
  HIGH: "warning",
  CRITICAL: "destructive",
};

const CHECKLIST_STATUSES: AuditChecklistItemStatus[] = [
  "NOT_STARTED",
  "IN_PROGRESS",
  "COMPLETED",
  "NOT_APPLICABLE",
  "REQUIRES_ATTENTION",
];

const ASSIGNMENT_ROLES: AuditAssignmentRole[] = ["LEAD_AUDITOR", "AUDITOR", "REVIEWER", "ACCOUNTANT", "CLIENT_CONTACT"];

export default function AuditEngagementDetailPage() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;

  const { data: engagement, isLoading } = useAuditEngagement(companyId, engagementId);

  if (!activeCompany || !companyId) return <EmptyCompanyState icon={ClipboardCheck} />;
  if (isLoading || !engagement || !engagementId) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="space-y-6">
      <Link to="/audits/engagements" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to engagements
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{engagement.engagement_code} — {engagement.title}</h1>
          <p className="text-sm text-muted-foreground">{engagement.period_start} to {engagement.period_end}</p>
        </div>
        <div className="flex items-center gap-2">
          {engagement.is_locked && <Badge variant="outline">Locked</Badge>}
          <Badge variant={STATUS_VARIANT[engagement.status]} className="text-sm">{engagement.status}</Badge>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="checklist">Checklist</TabsTrigger>
          <TabsTrigger value="findings">Findings</TabsTrigger>
          <TabsTrigger value="review">Review &amp; Sign-off</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab companyId={companyId} engagementId={engagementId} status={engagement.status} />
        </TabsContent>
        <TabsContent value="checklist">
          <ChecklistTab companyId={companyId} engagementId={engagementId} />
        </TabsContent>
        <TabsContent value="findings">
          <FindingsTab companyId={companyId} engagementId={engagementId} />
        </TabsContent>
        <TabsContent value="review">
          <ReviewTab companyId={companyId} engagementId={engagementId} status={engagement.status} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function OverviewTab({ companyId, engagementId, status }: { companyId: string; engagementId: string; status: AuditEngagementStatus }) {
  const { toast } = useToast();
  const { data: progress } = useAuditEngagementProgress(companyId, engagementId);
  const { data: assignments } = useAuditAssignments(companyId, engagementId);
  const { data: companyUsers } = useCompanyUsers(companyId);

  const open = useOpenAuditEngagement(companyId, engagementId);
  const startReview = useStartAuditEngagementReview(companyId, engagementId);
  const resumeReview = useResumeAuditEngagementReview(companyId, engagementId);
  const submitForReview = useSubmitAuditEngagementForReview(companyId, engagementId);
  const requestClientAction = useRequestAuditClientAction(companyId, engagementId);
  const approve = useApproveAuditEngagement(companyId, engagementId);
  const returnForChanges = useReturnAuditEngagementForChanges(companyId, engagementId);
  const close = useCloseAuditEngagement(companyId, engagementId);
  const lock = useLockAuditEngagement(companyId, engagementId);
  const cancel = useCancelAuditEngagement(companyId, engagementId);
  const assignUser = useAssignAuditEngagementUser(companyId, engagementId);
  const unassignUser = useUnassignAuditEngagementUser(companyId, engagementId);

  const [assignOpen, setAssignOpen] = useState(false);
  const [assignUserId, setAssignUserId] = useState("");
  const [assignRole, setAssignRole] = useState<AuditAssignmentRole>("AUDITOR");
  const [downloading, setDownloading] = useState(false);

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast({ title: message, variant: "success" });
    } catch (err) {
      toast({ title: "Action failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const download = async (format: "csv" | "xlsx") => {
    setDownloading(true);
    try {
      const { blob, filename } = await auditReportService.exportFindings(companyId, engagementId, format);
      triggerBlobDownload(blob, filename ?? `audit-findings.${format}`);
    } catch (err) {
      toast({ title: "Export failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  };

  const userLabel = (userId: string) => {
    const match = companyUsers?.items.find((u) => u.user_id === userId);
    return match ? `${match.first_name} ${match.last_name}` : userId.slice(0, 8);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
          {progress && (
            <div className="flex gap-6 text-sm">
              <div><p className="text-xs text-muted-foreground">Checklist</p><p className="font-semibold">{progress.checklist_completed}/{progress.checklist_total}</p></div>
              <div><p className="text-xs text-muted-foreground">Findings</p><p className="font-semibold">{progress.findings_total}</p></div>
              <div><p className="text-xs text-muted-foreground">Open Findings</p><p className="font-semibold">{progress.findings_open}</p></div>
              <div><p className="text-xs text-muted-foreground">High/Critical</p><p className="font-semibold">{(progress.findings_by_severity.HIGH ?? 0) + (progress.findings_by_severity.CRITICAL ?? 0)}</p></div>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            {status === "DRAFT" && (
              <PermissionGate permission="AUDIT_ENGAGEMENT_UPDATE">
                <Button size="sm" onClick={() => run(() => open.mutateAsync(), "Engagement opened")}>Open</Button>
              </PermissionGate>
            )}
            {(status === "OPEN" || status === "ASSIGNED") && (
              <PermissionGate permission="AUDIT_ENGAGEMENT_REVIEW">
                <Button size="sm" onClick={() => run(() => startReview.mutateAsync(), "Review started")}>Start Review</Button>
              </PermissionGate>
            )}
            {status === "IN_REVIEW" && (
              <>
                <PermissionGate permission="AUDIT_ENGAGEMENT_UPDATE">
                  <Button size="sm" variant="outline" onClick={() => run(() => requestClientAction.mutateAsync(undefined), "Pending client action")}>
                    Request Client Action
                  </Button>
                  <Button size="sm" onClick={() => run(() => submitForReview.mutateAsync(), "Submitted for auditor review")}>
                    Submit for Review
                  </Button>
                </PermissionGate>
              </>
            )}
            {status === "PENDING_CLIENT_ACTION" && (
              <PermissionGate permission="AUDIT_ENGAGEMENT_UPDATE">
                <Button size="sm" onClick={() => run(() => resumeReview.mutateAsync(), "Review resumed")}>Resume Review</Button>
              </PermissionGate>
            )}
            {status === "PENDING_AUDITOR_REVIEW" && (
              <PermissionGate permission="AUDIT_ENGAGEMENT_APPROVE">
                <Button size="sm" variant="outline" onClick={() => run(() => returnForChanges.mutateAsync(undefined), "Returned for changes")}>
                  Return for Changes
                </Button>
                <Button size="sm" onClick={() => run(() => approve.mutateAsync(undefined), "Engagement approved")}>Approve</Button>
              </PermissionGate>
            )}
            {status === "SIGNED_OFF" && (
              <PermissionGate permission="AUDIT_ENGAGEMENT_LOCK">
                <Button size="sm" onClick={() => run(() => close.mutateAsync(), "Engagement closed")}>Close</Button>
              </PermissionGate>
            )}
            {status === "CLOSED" && (
              <PermissionGate permission="AUDIT_ENGAGEMENT_LOCK">
                <Button size="sm" onClick={() => run(() => lock.mutateAsync(), "Engagement locked")}>Lock</Button>
              </PermissionGate>
            )}
            {["DRAFT", "OPEN", "ASSIGNED", "IN_REVIEW", "PENDING_CLIENT_ACTION"].includes(status) && (
              <PermissionGate permission="AUDIT_ENGAGEMENT_UPDATE">
                <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => run(() => cancel.mutateAsync(undefined), "Engagement cancelled")}>
                  Cancel
                </Button>
              </PermissionGate>
            )}
            <PermissionGate permission="AUDIT_REPORT_EXPORT">
              <Button size="sm" variant="outline" disabled={downloading} onClick={() => download("csv")}>
                <Download className="mr-1.5 h-3.5 w-3.5" /> CSV
              </Button>
              <Button size="sm" variant="outline" disabled={downloading} onClick={() => download("xlsx")}>
                <Download className="mr-1.5 h-3.5 w-3.5" /> XLSX
              </Button>
            </PermissionGate>
          </div>
        </CardContent>
      </Card>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Team</h2>
          <PermissionGate permission="AUDIT_ENGAGEMENT_ASSIGN">
            <Button size="sm" variant="outline" onClick={() => setAssignOpen(true)}>
              <Plus className="mr-1.5 h-3.5 w-3.5" /> Assign
            </Button>
          </PermissionGate>
        </div>
        <div className="rounded-lg border border-border bg-white">
          {assignments && assignments.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {assignments.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>{userLabel(a.user_id)}</TableCell>
                    <TableCell className="text-muted-foreground">{a.role.replaceAll("_", " ")}</TableCell>
                    <TableCell>
                      <Badge variant={a.is_active ? "success" : "outline"}>{a.is_active ? "Active" : "Removed"}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {a.is_active && (
                        <PermissionGate permission="AUDIT_ENGAGEMENT_ASSIGN">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:text-destructive"
                            onClick={() => run(() => unassignUser.mutateAsync(a.id), "Unassigned")}
                          >
                            Remove
                          </Button>
                        </PermissionGate>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyTableState icon={ClipboardCheck} title="No one assigned yet" />
          )}
        </div>
      </div>

      <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign a user</DialogTitle>
            <DialogDescription>The user must already have active access to this company.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>User</Label>
              <Select onValueChange={setAssignUserId} value={assignUserId}>
                <SelectTrigger><SelectValue placeholder="Select a user" /></SelectTrigger>
                <SelectContent>
                  {(companyUsers?.items ?? []).map((u) => (
                    <SelectItem key={u.user_id} value={u.user_id}>{u.first_name} {u.last_name} ({u.email})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Role</Label>
              <Select onValueChange={(v) => setAssignRole(v as AuditAssignmentRole)} value={assignRole}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ASSIGNMENT_ROLES.map((r) => <SelectItem key={r} value={r}>{r.replaceAll("_", " ")}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setAssignOpen(false)}>Cancel</Button>
            <Button
              type="button"
              disabled={!assignUserId || assignUser.isPending}
              onClick={async () => {
                try {
                  await assignUser.mutateAsync({ userId: assignUserId, role: assignRole });
                  toast({ title: "User assigned", variant: "success" });
                  setAssignOpen(false);
                  setAssignUserId("");
                } catch (err) {
                  toast({ title: "Assignment failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
                }
              }}
            >
              Assign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ChecklistTab({ companyId, engagementId }: { companyId: string; engagementId: string }) {
  const { toast } = useToast();
  const { data: checklist, isLoading } = useAuditChecklist(companyId, engagementId);
  const updateItem = useUpdateAuditChecklistItem(companyId, engagementId);

  if (isLoading || !checklist) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="rounded-lg border border-border bg-white">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Category</TableHead>
            <TableHead>Item</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {checklist.items.map((item) => (
            <TableRow key={item.id}>
              <TableCell className="text-muted-foreground">{item.category.replaceAll("_", " ")}</TableCell>
              <TableCell>
                <p className="font-medium">{item.title}</p>
                {item.description && <p className="text-xs text-muted-foreground">{item.description}</p>}
              </TableCell>
              <TableCell>
                <PermissionGate permission="AUDIT_CHECKLIST_MANAGE" fallback={<Badge variant="outline">{item.status.replaceAll("_", " ")}</Badge>}>
                  <Select
                    value={item.status}
                    onValueChange={async (value) => {
                      try {
                        await updateItem.mutateAsync({ itemId: item.id, payload: { status: value as AuditChecklistItemStatus } });
                      } catch (err) {
                        toast({ title: "Update failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
                      }
                    }}
                  >
                    <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {CHECKLIST_STATUSES.map((s) => <SelectItem key={s} value={s}>{s.replaceAll("_", " ")}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </PermissionGate>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

const findingSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  category: z.string().min(1),
  severity: z.string().min(1),
});
type FindingFormValues = z.infer<typeof findingSchema>;

const FINDING_CATEGORIES: AuditFindingCategory[] = [
  "ACCOUNTING", "GST", "TDS", "BANK", "DOCUMENT", "DATA_QUALITY", "CONTROL", "COMPLIANCE", "PROCESS", "OTHER",
];
const FINDING_SEVERITIES: AuditFindingSeverity[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

function FindingsTab({ companyId, engagementId }: { companyId: string; engagementId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useAuditFindingsForEngagement(companyId, engagementId);
  const createFinding = useCreateAuditFinding(companyId, engagementId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FindingFormValues>({ resolver: zodResolver(findingSchema), defaultValues: { severity: "MEDIUM", category: "ACCOUNTING" } });

  const onSubmit = async (values: FindingFormValues) => {
    setServerError(null);
    try {
      const result = await createFinding.mutateAsync({
        ...values,
        category: values.category as AuditFindingCategory,
        severity: values.severity as AuditFindingSeverity,
      });
      if (result.duplicate_warning) {
        toast({
          title: "Finding created — possible duplicate",
          description: `Open finding(s) already reference this source: ${result.duplicate_finding_codes.join(", ")}`,
        });
      } else {
        toast({ title: "Finding created", variant: "success" });
      }
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <PermissionGate permission="AUDIT_FINDING_CREATE">
          <Button size="sm" onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-3.5 w-3.5" /> New Finding
          </Button>
        </PermissionGate>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="p-6"><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((f) => (
                <TableRow key={f.id}>
                  <TableCell className="font-medium">
                    <Link to={`/audits/findings/${f.id}`} className="text-primary hover:underline">{f.finding_code}</Link>
                  </TableCell>
                  <TableCell>{f.title}</TableCell>
                  <TableCell className="text-muted-foreground">{f.category.replaceAll("_", " ")}</TableCell>
                  <TableCell><Badge variant={SEVERITY_VARIANT[f.severity]}>{f.severity}</Badge></TableCell>
                  <TableCell><Badge variant="outline">{f.status.replaceAll("_", " ")}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={ClipboardCheck} title="No findings yet" hint="Record an exception or observation." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New finding</DialogTitle>
            <DialogDescription>
              Record an observation for review — never labeled fraud or illegal here; use severity to flag urgency.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <p className="text-xs text-destructive">{serverError}</p>}
            <div className="space-y-1.5">
              <Label htmlFor="finding-title">Title</Label>
              <Input id="finding-title" {...register("title")} />
              {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="finding-description">Description</Label>
              <Textarea id="finding-description" rows={3} {...register("description")} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Category</Label>
                <Controller
                  control={control}
                  name="category"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {FINDING_CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c.replaceAll("_", " ")}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Severity</Label>
                <Controller
                  control={control}
                  name="severity"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {FINDING_SEVERITIES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
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

function ReviewTab({ companyId, engagementId, status }: { companyId: string; engagementId: string; status: AuditEngagementStatus }) {
  const { toast } = useToast();
  const { data: reviews } = useAuditReviews(companyId, engagementId);
  const { data: signoffs } = useAuditSignOffs(companyId, engagementId);
  const startReview = useStartAuditReview(companyId, engagementId);
  const completeReview = useCompleteAuditReview(companyId, engagementId);
  const createSignOff = useCreateAuditSignOff(companyId, engagementId);
  const markSignedOff = useMarkAuditEngagementSignedOff(companyId, engagementId);

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast({ title: message, variant: "success" });
    } catch (err) {
      toast({ title: "Action failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Review Passes</h2>
          <PermissionGate permission="AUDIT_ENGAGEMENT_REVIEW">
            <Button size="sm" variant="outline" onClick={() => run(() => startReview.mutateAsync("INITIAL_REVIEW"), "Review started")}>
              Start Review
            </Button>
          </PermissionGate>
        </div>
        <div className="rounded-lg border border-border bg-white">
          {reviews && reviews.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Summary</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reviews.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>{r.review_type.replaceAll("_", " ")}</TableCell>
                    <TableCell><Badge variant="outline">{r.status}</Badge></TableCell>
                    <TableCell className="text-muted-foreground">{r.summary ?? "—"}</TableCell>
                    <TableCell className="text-right">
                      {r.status === "IN_PROGRESS" && (
                        <PermissionGate permission="AUDIT_ENGAGEMENT_REVIEW">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => run(() => completeReview.mutateAsync({ reviewId: r.id, summary: "Review completed" }), "Review completed")}
                          >
                            Complete
                          </Button>
                        </PermissionGate>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyTableState icon={ClipboardCheck} title="No review passes yet" />
          )}
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Sign-offs</h2>
          {status === "APPROVED" && (
            <PermissionGate permission="AUDIT_ENGAGEMENT_SIGNOFF">
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => run(() => createSignOff.mutateAsync("LEAD_AUDITOR"), "Lead auditor sign-off recorded")}>
                  Lead Auditor Sign-off
                </Button>
                <Button size="sm" variant="outline" onClick={() => run(() => createSignOff.mutateAsync("REVIEWER"), "Reviewer sign-off recorded")}>
                  Reviewer Sign-off
                </Button>
                <Button size="sm" onClick={() => run(() => markSignedOff.mutateAsync(), "Marked signed off")}>Mark Signed Off</Button>
              </div>
            </PermissionGate>
          )}
        </div>
        <div className="space-y-2">
          {(signoffs ?? []).map((s) => (
            <Card key={s.id}>
              <CardContent className="pt-4">
                <div className="mb-1 flex items-center justify-between">
                  <Badge variant="success">{s.sign_off_type.replaceAll("_", " ")}</Badge>
                  <span className="text-xs text-muted-foreground">{new Date(s.created_at).toLocaleString()}</span>
                </div>
                <p className="text-sm text-muted-foreground">{s.statement}</p>
              </CardContent>
            </Card>
          ))}
          {(!signoffs || signoffs.length === 0) && (
            <p className="text-sm text-muted-foreground">No sign-offs recorded yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
