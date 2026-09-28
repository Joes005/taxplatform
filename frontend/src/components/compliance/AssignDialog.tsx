import { useState, useEffect } from "react";
import { UserCheck } from "lucide-react";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/useToast";
import { useCompanyUsers } from "@/hooks/useCompanyUsers";
import { useAssignComplianceObligation } from "@/hooks/useComplianceObligations";
import type { ComplianceObligation } from "@/types/compliance";

interface AssignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  companyId: string;
  obligation: ComplianceObligation | null;
}

export function AssignDialog({
  open,
  onOpenChange,
  companyId,
  obligation,
}: AssignDialogProps) {
  const { toast } = useToast();
  const { data: usersData, isLoading: isUsersLoading } = useCompanyUsers(companyId, 1, 100);
  const assignMutation = useAssignComplianceObligation(companyId);

  const [assignedTo, setAssignedTo] = useState<string>("none");
  const [reviewerId, setReviewerId] = useState<string>("none");

  useEffect(() => {
    if (obligation) {
      setAssignedTo(obligation.assigned_to || "none");
      setReviewerId(obligation.reviewer_id || "none");
    }
  }, [obligation]);

  if (!obligation) return null;

  const handleSave = async () => {
    try {
      await assignMutation.mutateAsync({
        obligationId: obligation.id,
        assignedTo: assignedTo === "none" ? undefined : assignedTo,
        reviewerId: reviewerId === "none" ? undefined : reviewerId,
      });
      toast({
        title: "Assignment updated",
        description: "Assigned owner and reviewer successfully.",
        variant: "success",
      });
      onOpenChange(false);
    } catch {
      toast({
        title: "Assignment failed",
        variant: "destructive",
      });
    }
  };

  const users = usersData?.items || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-primary" />
            <DialogTitle className="text-base font-semibold">Assign Obligation</DialogTitle>
          </div>
          <DialogDescription className="text-xs">
            Designate the primary owner and reviewer for <span className="font-semibold text-foreground">{obligation.name}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label className="text-xs">Primary Owner (Assignee)</Label>
            <Select value={assignedTo} onValueChange={setAssignedTo}>
              <SelectTrigger className="text-xs">
                <SelectValue placeholder={isUsersLoading ? "Loading users..." : "Select assignee"} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Unassigned</SelectItem>
                {users.map((u) => (
                  <SelectItem key={u.user_id} value={u.user_id} className="text-xs">
                    {u.first_name} {u.last_name} ({u.role_code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Reviewer (Auditor / CA / Admin)</Label>
            <Select value={reviewerId} onValueChange={setReviewerId}>
              <SelectTrigger className="text-xs">
                <SelectValue placeholder={isUsersLoading ? "Loading users..." : "Select reviewer"} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No Reviewer</SelectItem>
                {users.map((u) => (
                  <SelectItem key={u.user_id} value={u.user_id} className="text-xs">
                    {u.first_name} {u.last_name} ({u.role_code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={assignMutation.isPending} onClick={handleSave}>
            {assignMutation.isPending ? "Saving..." : "Save Assignment"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
