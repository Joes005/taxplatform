import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CalendarClock } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCompanyUsers } from "@/hooks/useCompanyUsers";
import { useDocuments } from "@/hooks/useDocuments";
import {
  useAddComplianceTaskComment,
  useAddComplianceTaskEvidence,
  useCancelComplianceTask,
  useCompleteComplianceTask,
  useComplianceTask,
  useComplianceTaskComments,
  useComplianceTaskEvidence,
  useLockComplianceTask,
  useRemoveComplianceTaskEvidence,
  useReturnComplianceTaskForChanges,
  useStartComplianceTask,
  useSubmitComplianceTaskForReview,
  useVerifyComplianceTask,
} from "@/hooks/useComplianceTasks";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api-client";
import type { ComplianceTaskStatus } from "@/types/compliance";

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

export default function ComplianceTaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  if (!activeCompany) return <CalendarClock className="h-6 w-6" />;
  const companyId = activeCompany.company_id;

  const { data: task, isLoading } = useComplianceTask(companyId, taskId);
  const { data: comments } = useComplianceTaskComments(companyId, taskId);
  const { data: evidence } = useComplianceTaskEvidence(companyId, taskId);
  const { data: companyUsers } = useCompanyUsers(companyId);
  const { data: documents } = useDocuments(companyId ? { companyId, pageSize: 100 } : null);

  const start = useStartComplianceTask(companyId, taskId ?? "");
  const submitReview = useSubmitComplianceTaskForReview(companyId, taskId ?? "");
  const complete = useCompleteComplianceTask(companyId, taskId ?? "");
  const verify = useVerifyComplianceTask(companyId, taskId ?? "");
  const returnForChanges = useReturnComplianceTaskForChanges(companyId, taskId ?? "");
  const cancel = useCancelComplianceTask(companyId, taskId ?? "");
  const lock = useLockComplianceTask(companyId, taskId ?? "");
  const addComment = useAddComplianceTaskComment(companyId, taskId ?? "");
  const addEvidence = useAddComplianceTaskEvidence(companyId, taskId ?? "");
  const removeEvidence = useRemoveComplianceTaskEvidence(companyId, taskId ?? "");

  const [commentText, setCommentText] = useState("");
  const [completionNotes, setCompletionNotes] = useState("");
  const [returnReason, setReturnReason] = useState("");
  const [evidenceDoc, setEvidenceDoc] = useState("");

  if (isLoading || !task || !taskId) return <Skeleton className="h-96 w-full" />;

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast({ title: message, variant: "success" });
    } catch (err) {
      toast({ title: "Action failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const userLabel = (userId: string | null) => {
    if (!userId) return "Unassigned";
    const match = companyUsers?.items.find((u) => u.user_id === userId);
    return match ? `${match.first_name} ${match.last_name}` : userId.slice(0, 8);
  };

  const status = task.status;

  return (
    <div className="space-y-6">
      <Link to="/compliance/tasks" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to tasks
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{task.title}</h1>
          <p className="text-sm text-muted-foreground">
            {task.category.replaceAll("_", " ")} · Due {task.due_date} · Assigned to {userLabel(task.assigned_to)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {task.is_overdue && <Badge variant="destructive">Overdue</Badge>}
          <Badge variant={STATUS_VARIANT[status]} className="text-sm">{status.replaceAll("_", " ")}</Badge>
        </div>
      </div>

      {task.description && (
        <Card><CardContent className="pt-6 text-sm text-muted-foreground">{task.description}</CardContent></Card>
      )}

      <Card>
        <CardContent className="flex flex-wrap items-center gap-2 pt-6">
          {(status === "PENDING" || status === "OVERDUE") && (
            <PermissionGate permission="COMPLIANCE_TASK_UPDATE">
              <Button size="sm" onClick={() => run(() => start.mutateAsync(), "Task started")}>Start</Button>
            </PermissionGate>
          )}
          {(status === "IN_PROGRESS" || status === "OVERDUE") && (
            <PermissionGate permission="COMPLIANCE_TASK_COMPLETE">
              <Button size="sm" variant="outline" onClick={() => run(() => submitReview.mutateAsync(), "Submitted for review")}>
                Submit for Review
              </Button>
            </PermissionGate>
          )}
          {(status === "IN_PROGRESS" || status === "OVERDUE") && (
            <PermissionGate permission="COMPLIANCE_TASK_COMPLETE">
              <Button size="sm" onClick={() => run(() => complete.mutateAsync(completionNotes || undefined), "Task completed")}>
                Complete
              </Button>
            </PermissionGate>
          )}
          {(status === "PENDING_REVIEW" || status === "COMPLETED") && (
            <PermissionGate permission="COMPLIANCE_TASK_VERIFY">
              <Button size="sm" onClick={() => run(() => verify.mutateAsync(), "Task verified")}>Verify</Button>
            </PermissionGate>
          )}
          {(status === "VERIFIED" || status === "COMPLETED") && (
            <PermissionGate permission="COMPLIANCE_TASK_LOCK">
              <Button size="sm" onClick={() => run(() => lock.mutateAsync(), "Task locked")}>Lock</Button>
            </PermissionGate>
          )}
          {["PENDING", "IN_PROGRESS", "OVERDUE"].includes(status) && (
            <PermissionGate permission="COMPLIANCE_TASK_CANCEL">
              <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => run(() => cancel.mutateAsync(undefined), "Task cancelled")}>
                Cancel
              </Button>
            </PermissionGate>
          )}
        </CardContent>
      </Card>

      {["IN_PROGRESS", "OVERDUE"].includes(status) && (
        <Card>
          <CardContent className="space-y-2 pt-6">
            <Label>Completion notes (optional)</Label>
            <Textarea rows={2} value={completionNotes} onChange={(e) => setCompletionNotes(e.target.value)} />
          </CardContent>
        </Card>
      )}

      {status === "PENDING_REVIEW" && (
        <Card>
          <CardContent className="space-y-2 pt-6">
            <Label>Return for changes</Label>
            <div className="flex items-end gap-2">
              <Textarea rows={2} className="flex-1" value={returnReason} onChange={(e) => setReturnReason(e.target.value)} placeholder="Reason…" />
              <PermissionGate permission="COMPLIANCE_TASK_REVIEW">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!returnReason}
                  onClick={async () => {
                    await run(() => returnForChanges.mutateAsync(returnReason), "Returned for changes");
                    setReturnReason("");
                  }}
                >
                  Return
                </Button>
              </PermissionGate>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="space-y-3 pt-6">
          <h2 className="text-sm font-semibold">Evidence</h2>
          <div className="space-y-2">
            {(evidence ?? []).map((e) => (
              <div key={e.id} className="flex items-center justify-between rounded-md border border-border p-2 text-sm">
                <span>{e.description || "Attached document"}</span>
                <PermissionGate permission="COMPLIANCE_TASK_UPDATE">
                  <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => removeEvidence.mutate(e.id)}>
                    Remove
                  </Button>
                </PermissionGate>
              </div>
            ))}
            {(!evidence || evidence.length === 0) && <p className="text-sm text-muted-foreground">No evidence attached yet.</p>}
          </div>
          <PermissionGate permission="COMPLIANCE_TASK_UPDATE">
            <div className="flex items-end gap-2">
              <div className="flex-1 space-y-1.5">
                <Label>Attach an existing document</Label>
                <Select value={evidenceDoc} onValueChange={setEvidenceDoc}>
                  <SelectTrigger><SelectValue placeholder="Select a document" /></SelectTrigger>
                  <SelectContent>
                    {(documents?.items ?? []).map((d) => <SelectItem key={d.id} value={d.id}>{d.original_filename}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <Button
                size="sm"
                disabled={!evidenceDoc}
                onClick={async () => {
                  await run(() => addEvidence.mutateAsync({ documentId: evidenceDoc }), "Evidence added");
                  setEvidenceDoc("");
                }}
              >
                Attach
              </Button>
            </div>
          </PermissionGate>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3 pt-6">
          <h2 className="text-sm font-semibold">Comments</h2>
          <div className="space-y-2">
            {(comments ?? []).map((c) => (
              <div key={c.id} className="rounded-md border border-border p-2 text-sm">
                <p className="mb-1 text-xs text-muted-foreground">{userLabel(c.user_id)} · {new Date(c.created_at).toLocaleString()}</p>
                <p>{c.comment}</p>
              </div>
            ))}
            {(!comments || comments.length === 0) && <p className="text-sm text-muted-foreground">No comments yet.</p>}
          </div>
          <PermissionGate permission="COMPLIANCE_TASK_UPDATE">
            <div className="flex items-end gap-2">
              <div className="flex-1 space-y-1.5">
                <Label>Add a comment</Label>
                <Textarea rows={2} value={commentText} onChange={(e) => setCommentText(e.target.value)} />
              </div>
              <Button
                size="sm"
                disabled={!commentText}
                onClick={async () => {
                  await run(() => addComment.mutateAsync(commentText), "Comment added");
                  setCommentText("");
                }}
              >
                Post
              </Button>
            </div>
          </PermissionGate>
        </CardContent>
      </Card>
    </div>
  );
}
