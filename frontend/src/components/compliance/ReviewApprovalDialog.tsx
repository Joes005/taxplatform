import { useState } from "react";
import { CheckCircle2, XCircle, Send, RotateCcw, AlertTriangle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/useToast";
import {
  useSubmitObligationReview,
  useApproveObligation,
  useRejectObligation,
  useCompleteObligation,
  useReopenObligation,
} from "@/hooks/useComplianceObligations";
import type { ComplianceObligation } from "@/types/compliance";
import { ApiError } from "@/lib/api-client";

export type ReviewActionType = "SUBMIT" | "APPROVE" | "REJECT" | "COMPLETE" | "REOPEN";

interface ReviewApprovalDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  companyId: string;
  obligation: ComplianceObligation | null;
  actionType: ReviewActionType;
}

export function ReviewApprovalDialog({
  open,
  onOpenChange,
  companyId,
  obligation,
  actionType,
}: ReviewApprovalDialogProps) {
  const { toast } = useToast();
  const [notes, setNotes] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const obligationId = obligation?.id || "";

  const submitReviewMutation = useSubmitObligationReview(companyId);
  const approveMutation = useApproveObligation(companyId);
  const rejectMutation = useRejectObligation(companyId);
  const completeMutation = useCompleteObligation(companyId);
  const reopenMutation = useReopenObligation(companyId);

  if (!obligation) return null;

  const isPending =
    submitReviewMutation.isPending ||
    approveMutation.isPending ||
    rejectMutation.isPending ||
    completeMutation.isPending ||
    reopenMutation.isPending;

  const handleSubmit = async () => {
    setErrorMsg(null);
    try {
      if (actionType === "SUBMIT") {
        await submitReviewMutation.mutateAsync({ obligationId, reviewNotes: notes || undefined });
        toast({ title: "Submitted for review", variant: "success" });
      } else if (actionType === "APPROVE") {
        await approveMutation.mutateAsync({ obligationId, reviewNotes: notes || undefined });
        toast({ title: "Obligation approved", variant: "success" });
      } else if (actionType === "REJECT") {
        if (!notes.trim()) {
          setErrorMsg("A rejection reason is required.");
          return;
        }
        await rejectMutation.mutateAsync({ obligationId, reviewNotes: notes });
        toast({ title: "Obligation returned for changes", variant: "default" });
      } else if (actionType === "COMPLETE") {
        await completeMutation.mutateAsync({ obligationId, completionNotes: notes || undefined });
        toast({ title: "Obligation marked as completed", variant: "success" });
      } else if (actionType === "REOPEN") {
        await reopenMutation.mutateAsync({ obligationId, reason: notes || "Reopened by user" });
        toast({ title: "Obligation reopened", variant: "success" });
      }
      setNotes("");
      onOpenChange(false);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Action failed. Check prerequisites and permissions.";
      setErrorMsg(msg);
      toast({ title: "Operation failed", description: msg, variant: "destructive" });
    }
  };

  const getActionConfig = () => {
    switch (actionType) {
      case "SUBMIT":
        return {
          title: "Submit for Review",
          description: `Submit ${obligation.name} for CA / Auditor verification and review.`,
          icon: Send,
          confirmLabel: "Submit for Review",
          variant: "default" as const,
          placeholder: "Add remarks for reviewer regarding evidence or calculations...",
        };
      case "APPROVE":
        return {
          title: "Approve Compliance Obligation",
          description: `Sign off and approve ${obligation.name}. This confirms all prerequisites and evidence are in order.`,
          icon: CheckCircle2,
          confirmLabel: "Approve Obligation",
          variant: "default" as const,
          placeholder: "Optional approval remarks or verification notes...",
        };
      case "REJECT":
        return {
          title: "Reject / Return for Changes",
          description: `Return ${obligation.name} to the owner with comments detailing what needs correction.`,
          icon: XCircle,
          confirmLabel: "Reject & Request Changes",
          variant: "destructive" as const,
          placeholder: "Specify why this was rejected and what remediation is required...",
        };
      case "COMPLETE":
        return {
          title: "Complete Compliance Obligation",
          description: `Mark ${obligation.name} as fully satisfied and completed.`,
          icon: CheckCircle2,
          confirmLabel: "Mark as Completed",
          variant: "default" as const,
          placeholder: "Optional completion notes or reference numbers...",
        };
      case "REOPEN":
        return {
          title: "Reopen Compliance Obligation",
          description: `Reopen ${obligation.name} back to In Progress state for additional modifications.`,
          icon: RotateCcw,
          confirmLabel: "Reopen Obligation",
          variant: "secondary" as const,
          placeholder: "Reason for reopening this completed obligation...",
        };
    }
  };

  const config = getActionConfig();
  const Icon = config.icon;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-primary" />
            <DialogTitle className="text-base font-semibold">{config.title}</DialogTitle>
          </div>
          <DialogDescription className="text-xs">{config.description}</DialogDescription>
        </DialogHeader>

        {errorMsg && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 p-2.5 text-xs text-destructive flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="space-y-3 py-1">
          <div className="space-y-1.5">
            <Label className="text-xs">
              {actionType === "REJECT" ? "Rejection Reason (Required)" : "Notes / Remarks (Optional)"}
            </Label>
            <Textarea
              className="text-xs min-h-[90px]"
              placeholder={config.placeholder}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            variant={config.variant}
            disabled={isPending || (actionType === "REJECT" && !notes.trim())}
            onClick={handleSubmit}
          >
            {isPending ? "Processing..." : config.confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
