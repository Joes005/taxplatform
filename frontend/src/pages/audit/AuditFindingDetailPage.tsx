import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ClipboardCheck } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCompanyUsers } from "@/hooks/useCompanyUsers";
import { useDocuments } from "@/hooks/useDocuments";
import {
  useAddAuditFindingComment,
  useAddAuditFindingEvidence,
  useAssignAuditFinding,
  useAuditFinding,
  useAuditFindingComments,
  useAuditFindingEvidence,
  useAuditFindingResponses,
  useCloseAuditFinding,
  useRejectAuditFinding,
  useRemoveAuditFindingEvidence,
  useReopenAuditFinding,
  useResolveAuditFinding,
  useReviewAuditFindingResponse,
  useSubmitAuditFindingResponse,
} from "@/hooks/useAuditFindings";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api-client";
import type { AuditFindingSeverity, AuditFindingStatus } from "@/types/audit";

const SEVERITY_VARIANT: Record<AuditFindingSeverity, "secondary" | "warning" | "destructive"> = {
  LOW: "secondary",
  MEDIUM: "secondary",
  HIGH: "warning",
  CRITICAL: "destructive",
};

const STATUS_VARIANT: Record<AuditFindingStatus, "secondary" | "warning" | "success" | "outline" | "destructive"> = {
  OPEN: "secondary",
  ASSIGNED: "secondary",
  IN_REVIEW: "warning",
  ACTION_REQUIRED: "warning",
  RESPONSE_SUBMITTED: "warning",
  RESOLVED: "success",
  REOPENED: "warning",
  CLOSED: "success",
  REJECTED: "outline",
};

export default function AuditFindingDetailPage() {
  const { findingId } = useParams<{ findingId: string }>();
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  if (!activeCompany) return <ClipboardCheck className="h-6 w-6" />;
  const companyId = activeCompany.company_id;

  const { data: finding, isLoading } = useAuditFinding(companyId, findingId);
  const { data: comments } = useAuditFindingComments(companyId, findingId);
  const { data: evidence } = useAuditFindingEvidence(companyId, findingId);
  const { data: responses } = useAuditFindingResponses(companyId, findingId);
  const { data: companyUsers } = useCompanyUsers(companyId);
  const { data: documents } = useDocuments(companyId ? { companyId, pageSize: 100 } : null);

  const assign = useAssignAuditFinding(companyId, findingId ?? "");
  const resolve = useResolveAuditFinding(companyId, findingId ?? "");
  const close = useCloseAuditFinding(companyId, findingId ?? "");
  const reopen = useReopenAuditFinding(companyId, findingId ?? "");
  const reject = useRejectAuditFinding(companyId, findingId ?? "");
  const addComment = useAddAuditFindingComment(companyId, findingId ?? "");
  const addEvidence = useAddAuditFindingEvidence(companyId, findingId ?? "");
  const removeEvidence = useRemoveAuditFindingEvidence(companyId, findingId ?? "");
  const submitResponse = useSubmitAuditFindingResponse(companyId, findingId ?? "");
  const reviewResponse = useReviewAuditFindingResponse(companyId, findingId ?? "");

  const [commentText, setCommentText] = useState("");
  const [responseText, setResponseText] = useState("");
  const [resolutionSummary, setResolutionSummary] = useState("");
  const [reasonText, setReasonText] = useState("");
  const [assignTo, setAssignTo] = useState("");
  const [evidenceDoc, setEvidenceDoc] = useState("");

  if (isLoading || !finding || !findingId) return <Skeleton className="h-64 w-full" />;

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast({ title: message, variant: "success" });
    } catch (err) {
      toast({ title: "Action failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const userLabel = (userId: string) => {
    const match = companyUsers?.items.find((u) => u.user_id === userId);
    return match ? `${match.first_name} ${match.last_name}` : userId.slice(0, 8);
  };

  const pendingResponse = responses?.find((r) => r.status === "SUBMITTED");

  return (
    <div className="space-y-6">
      <Link to={`/audits/engagements/${finding.engagement_id}`} className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to engagement
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{finding.finding_code} — {finding.title}</h1>
          <p className="text-sm text-muted-foreground">{finding.category.replaceAll("_", " ")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={SEVERITY_VARIANT[finding.severity]}>{finding.severity}</Badge>
          <Badge variant={STATUS_VARIANT[finding.status]}>{finding.status.replaceAll("_", " ")}</Badge>
        </div>
      </div>

      {finding.description && (
        <Card><CardContent className="pt-6 text-sm text-muted-foreground">{finding.description}</CardContent></Card>
      )}

      <Card>
        <CardContent className="space-y-3 pt-6">
          {(["OPEN", "ASSIGNED", "IN_REVIEW", "ACTION_REQUIRED", "RESPONSE_SUBMITTED"].includes(finding.status) ||
            ["RESOLVED", "CLOSED", "REJECTED"].includes(finding.status)) && (
            <div className="space-y-1.5">
              <Label htmlFor="reason-text">Reason (used for reject/reopen)</Label>
              <Textarea id="reason-text" rows={2} value={reasonText} onChange={(e) => setReasonText(e.target.value)} />
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <PermissionGate permission="AUDIT_FINDING_ASSIGN">
              <Select value={assignTo} onValueChange={setAssignTo}>
                <SelectTrigger className="w-56"><SelectValue placeholder="Assign to…" /></SelectTrigger>
                <SelectContent>
                  {(companyUsers?.items ?? []).map((u) => (
                    <SelectItem key={u.user_id} value={u.user_id}>{u.first_name} {u.last_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="sm"
                variant="outline"
                disabled={!assignTo}
                onClick={() => run(() => assign.mutateAsync(assignTo), "Finding assigned")}
              >
                Assign
              </Button>
            </PermissionGate>

            {["OPEN", "ASSIGNED", "IN_REVIEW", "ACTION_REQUIRED", "RESPONSE_SUBMITTED"].includes(finding.status) && (
              <PermissionGate permission="AUDIT_FINDING_RESOLVE">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!reasonText}
                  className="text-destructive hover:text-destructive"
                  onClick={async () => {
                    await run(() => reject.mutateAsync(reasonText), "Finding rejected");
                    setReasonText("");
                  }}
                >
                  Reject
                </Button>
              </PermissionGate>
            )}

            {["RESOLVED", "CLOSED", "REJECTED"].includes(finding.status) && (
              <PermissionGate permission="AUDIT_FINDING_REOPEN">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!reasonText}
                  onClick={async () => {
                    await run(() => reopen.mutateAsync(reasonText), "Finding reopened");
                    setReasonText("");
                  }}
                >
                  Reopen
                </Button>
              </PermissionGate>
            )}

            {finding.status === "RESOLVED" && (
              <PermissionGate permission="AUDIT_FINDING_RESOLVE">
                <Button size="sm" onClick={() => run(() => close.mutateAsync(), "Finding closed")}>Close</Button>
              </PermissionGate>
            )}
          </div>

          {["OPEN", "ASSIGNED", "IN_REVIEW", "ACTION_REQUIRED", "RESPONSE_SUBMITTED"].includes(finding.status) && (
            <PermissionGate permission="AUDIT_FINDING_RESOLVE">
              <div className="flex items-end gap-2">
                <div className="flex-1 space-y-1.5">
                  <Label htmlFor="resolution-summary">Resolution summary</Label>
                  <Textarea id="resolution-summary" rows={2} value={resolutionSummary} onChange={(e) => setResolutionSummary(e.target.value)} />
                </div>
                <Button
                  size="sm"
                  disabled={!resolutionSummary}
                  onClick={() => run(() => resolve.mutateAsync(resolutionSummary), "Finding resolved")}
                >
                  Resolve
                </Button>
              </div>
            </PermissionGate>
          )}
        </CardContent>
      </Card>

      {(finding.status === "ASSIGNED" || finding.status === "ACTION_REQUIRED") && (
        <Card>
          <CardContent className="space-y-3 pt-6">
            <h2 className="text-sm font-semibold">Submit a response</h2>
            <Textarea rows={3} value={responseText} onChange={(e) => setResponseText(e.target.value)} placeholder="Describe how this was addressed…" />
            <PermissionGate permission="AUDIT_FINDING_RESPOND">
              <Button
                size="sm"
                disabled={!responseText}
                onClick={async () => {
                  await run(() => submitResponse.mutateAsync(responseText), "Response submitted");
                  setResponseText("");
                }}
              >
                Submit Response
              </Button>
            </PermissionGate>
          </CardContent>
        </Card>
      )}

      {pendingResponse && (
        <Card>
          <CardContent className="space-y-3 pt-6">
            <h2 className="text-sm font-semibold">Pending response</h2>
            <p className="text-sm text-muted-foreground">{pendingResponse.response_text}</p>
            <PermissionGate permission="AUDIT_FINDING_REVIEW">
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => run(() => reviewResponse.mutateAsync({ responseId: pendingResponse.id, accept: false }), "Response rejected")}
                >
                  Reject Response
                </Button>
                <Button
                  size="sm"
                  onClick={() => run(() => reviewResponse.mutateAsync({ responseId: pendingResponse.id, accept: true }), "Response accepted — finding resolved")}
                >
                  Accept &amp; Resolve
                </Button>
              </div>
            </PermissionGate>
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
                <PermissionGate permission="AUDIT_EVIDENCE_MANAGE">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive hover:text-destructive"
                    onClick={() => run(() => removeEvidence.mutateAsync(e.id), "Evidence removed")}
                  >
                    Remove
                  </Button>
                </PermissionGate>
              </div>
            ))}
            {(!evidence || evidence.length === 0) && <p className="text-sm text-muted-foreground">No evidence attached yet.</p>}
          </div>
          <PermissionGate permission="AUDIT_EVIDENCE_MANAGE">
            <div className="flex items-end gap-2">
              <div className="flex-1 space-y-1.5">
                <Label>Attach an existing document</Label>
                <Select value={evidenceDoc} onValueChange={setEvidenceDoc}>
                  <SelectTrigger><SelectValue placeholder="Select a document" /></SelectTrigger>
                  <SelectContent>
                    {(documents?.items ?? []).map((d) => (
                      <SelectItem key={d.id} value={d.id}>{d.original_filename}</SelectItem>
                    ))}
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
          <PermissionGate permission="AUDIT_FINDING_UPDATE">
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
