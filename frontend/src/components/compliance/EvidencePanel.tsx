import { useState } from "react";
import { FileText, Paperclip, Trash2, Download, Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/useToast";
import { useDocuments } from "@/hooks/useDocuments";
import { useObligationEvidence, useAttachObligationEvidence, useRemoveObligationEvidence } from "@/hooks/useComplianceObligations";
import type { ComplianceObligation } from "@/types/compliance";
import { triggerBlobDownload } from "@/lib/utils";
import { documentService } from "@/services/documentService";

interface EvidencePanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  companyId: string;
  obligation: ComplianceObligation | null;
}

export function EvidencePanel({
  open,
  onOpenChange,
  companyId,
  obligation,
}: EvidencePanelProps) {
  const { toast } = useToast();
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [description, setDescription] = useState<string>("");

  const obligationId = obligation?.id || "";
  const { data: evidenceList, isLoading: isEvidenceLoading } = useObligationEvidence(
    companyId,
    obligationId
  );
  const { data: docData, isLoading: isDocsLoading } = useDocuments(
    companyId ? { companyId, page: 1, pageSize: 50 } : null
  );

  const attachMutation = useAttachObligationEvidence(companyId);
  const removeMutation = useRemoveObligationEvidence(companyId);

  if (!obligation) return null;

  const handleAttach = async () => {
    if (!selectedDocId) return;
    try {
      await attachMutation.mutateAsync({
        obligationId,
        documentId: selectedDocId,
        description: description || undefined,
      });
      setSelectedDocId("");
      setDescription("");
      toast({
        title: "Evidence attached",
        description: "Document successfully linked to compliance obligation.",
        variant: "success",
      });
    } catch {
      toast({
        title: "Failed to attach evidence",
        variant: "destructive",
      });
    }
  };

  const handleRemove = async (evidenceId: string) => {
    try {
      await removeMutation.mutateAsync({ obligationId, evidenceId });
      toast({
        title: "Evidence removed",
        variant: "success",
      });
    } catch {
      toast({
        title: "Failed to remove evidence",
        variant: "destructive",
      });
    }
  };

  const handleDownload = async (docId: string, filename?: string) => {
    try {
      const res = await documentService.download(companyId, docId);
      triggerBlobDownload(res.blob, res.filename || filename || `document-${docId}`);
    } catch {
      toast({
        title: "Download failed",
        variant: "destructive",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Paperclip className="h-5 w-5 text-primary" />
            <DialogTitle className="text-lg font-semibold">Compliance Evidence</DialogTitle>
          </div>
          <DialogDescription className="text-xs">
            Review and link supporting documents, audit trails, and challan receipts for{" "}
            <span className="font-semibold text-foreground">{obligation.name}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Attached Evidence ({evidenceList?.length || 0})
            </h4>

            {isEvidenceLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : !evidenceList || evidenceList.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
                No supporting evidence attached yet. Link documents below before submitting for CA/Auditor review.
              </div>
            ) : (
              <div className="space-y-2">
                {evidenceList.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between rounded-lg border border-border p-3 text-xs bg-card"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div>
                        <div className="font-medium text-foreground">
                          {item.document?.original_filename || "Document"}
                        </div>
                        {item.description && (
                          <div className="text-muted-foreground text-[11px]">{item.description}</div>
                        )}
                        <div className="text-[10px] text-muted-foreground">
                          Attached on {new Date(item.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        title="Download Document"
                        onClick={() => handleDownload(item.document_id, item.document?.original_filename)}
                      >
                        <Download className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                        title="Remove Evidence"
                        disabled={removeMutation.isPending}
                        onClick={() => handleRemove(item.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/80 bg-muted/20 p-3 space-y-3">
            <h4 className="text-xs font-semibold flex items-center gap-1.5 text-foreground">
              <Plus className="h-3.5 w-3.5 text-primary" /> Attach Document from Repository
            </h4>
            <div className="space-y-2">
              <div className="space-y-1">
                <Label className="text-xs">Select Document</Label>
                <Select value={selectedDocId} onValueChange={setSelectedDocId}>
                  <SelectTrigger className="text-xs h-9">
                    <SelectValue placeholder={isDocsLoading ? "Loading documents..." : "Select document"} />
                  </SelectTrigger>
                  <SelectContent>
                    {(docData?.items ?? []).map((doc) => (
                      <SelectItem key={doc.id} value={doc.id} className="text-xs">
                        {doc.original_filename} ({doc.document_type || "General"})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <Label className="text-xs">Evidence Description / Note (Optional)</Label>
                <Input
                  className="text-xs h-9"
                  placeholder="e.g. Challan receipt, filed acknowledgement, sign-off sheet"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div className="flex justify-end pt-1">
                <Button
                  size="sm"
                  className="h-8 text-xs"
                  disabled={!selectedDocId || attachMutation.isPending}
                  onClick={handleAttach}
                >
                  {attachMutation.isPending ? "Attaching..." : "Attach Evidence"}
                </Button>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="mt-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
