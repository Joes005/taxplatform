import { useEffect, useState } from "react";
import {
  Archive,
  ArchiveRestore,
  Download,
  FileText,
  Image as ImageIcon,
  ScrollText,
} from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useDocument, useArchiveDocument, useRestoreDocument } from "@/hooks/useDocuments";
import { useAuditLogs } from "@/hooks/useAuditLogs";
import { documentService } from "@/services/documentService";
import { PermissionGate } from "@/components/PermissionGate";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatDateTime, formatFileSize, triggerBlobDownload } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";
import {
  DOCUMENT_STATUS_BADGE_VARIANT,
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_TYPE_LABELS,
} from "./documentConstants";

interface DocumentDetailsDialogProps {
  documentId: string | null;
  onOpenChange: (open: boolean) => void;
}

const PREVIEWABLE_EXTENSIONS = new Set(["pdf", "jpg", "jpeg", "png"]);

export function DocumentDetailsDialog({ documentId, onOpenChange }: DocumentDetailsDialogProps) {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id;

  const { data: document, isLoading } = useDocument(companyId, documentId ?? undefined);
  const archiveMutation = useArchiveDocument(companyId ?? "");
  const restoreMutation = useRestoreDocument(companyId ?? "");

  const { data: auditData } = useAuditLogs(
    companyId && documentId
      ? { companyId, resourceType: "document", resourceId: documentId, pageSize: 10 }
      : null
  );

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [confirmArchiveOpen, setConfirmArchiveOpen] = useState(false);

  const canPreview = document ? PREVIEWABLE_EXTENSIONS.has(document.file_extension) : false;

  useEffect(() => {
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });

    if (!document || !companyId || !canPreview) return;

    let cancelled = false;
    setPreviewLoading(true);
    documentService
      .download(companyId, document.id)
      .then(({ blob }) => {
        if (cancelled) return;
        setPreviewUrl(URL.createObjectURL(blob));
      })
      .catch(() => {
        if (!cancelled) setPreviewUrl(null);
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [document?.id, companyId, canPreview]);

  const handleDownload = async () => {
    if (!companyId || !document) return;
    try {
      const { blob, filename } = await documentService.download(companyId, document.id);
      triggerBlobDownload(blob, filename ?? document.original_filename);
    } catch (err) {
      toast({
        title: "Download failed",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "destructive",
      });
    }
  };

  const handleArchive = async () => {
    if (!documentId) return;
    await archiveMutation.mutateAsync(documentId);
    toast({ title: "Document archived", variant: "success" });
  };

  const handleRestore = async () => {
    if (!documentId) return;
    try {
      await restoreMutation.mutateAsync(documentId);
      toast({ title: "Document restored", variant: "success" });
    } catch (err) {
      toast({
        title: "Could not restore document",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "destructive",
      });
    }
  };

  return (
    <Dialog open={!!documentId} onOpenChange={(open) => !open && onOpenChange(false)}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 truncate">
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate">{document?.original_filename ?? "Document details"}</span>
          </DialogTitle>
          <DialogDescription>Metadata, preview, and activity for this document</DialogDescription>
        </DialogHeader>

        {isLoading || !document ? (
          <div className="space-y-3">
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center gap-2">
              <Badge variant={DOCUMENT_STATUS_BADGE_VARIANT[document.status]}>
                {DOCUMENT_STATUS_LABELS[document.status]}
              </Badge>
              <Badge variant="outline">{DOCUMENT_TYPE_LABELS[document.document_type]}</Badge>
            </div>

            <div className="overflow-hidden rounded-md border border-border bg-muted">
              {!canPreview ? (
                <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-sm text-muted-foreground">
                  <ImageIcon className="h-8 w-8" />
                  This file type cannot be previewed here. Download to view.
                </div>
              ) : previewLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : !previewUrl ? (
                <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-sm text-muted-foreground">
                  Preview unavailable. Download to view.
                </div>
              ) : document.file_extension === "pdf" ? (
                <iframe src={previewUrl} title={document.original_filename} className="h-96 w-full" />
              ) : (
                <img
                  src={previewUrl}
                  alt={document.original_filename}
                  className="mx-auto max-h-96 object-contain"
                />
              )}
            </div>

            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
              <Field label="Size" value={formatFileSize(document.file_size)} />
              <Field label="Uploaded by" value={`${document.uploaded_by.first_name} ${document.uploaded_by.last_name}`} />
              <Field label="Uploaded at" value={formatDateTime(document.uploaded_at)} />
              <Field label="MIME type" value={document.mime_type} />
              <Field label="Archived at" value={formatDateTime(document.archived_at)} />
              <Field label="Checksum (SHA-256)" value={document.checksum} mono className="col-span-2 sm:col-span-3" />
              {document.description && (
                <Field label="Description" value={document.description} className="col-span-2 sm:col-span-3" />
              )}
            </dl>

            {auditData && auditData.items.length > 0 && (
              <div>
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <ScrollText className="h-3.5 w-3.5" /> Activity
                </p>
                <ul className="space-y-1.5 text-xs">
                  {auditData.items.map((log) => (
                    <li key={log.id} className="flex items-center justify-between text-muted-foreground">
                      <span className="font-medium text-foreground">{log.action.replace(/_/g, " ")}</span>
                      <span>{formatDateTime(log.created_at)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex flex-wrap justify-end gap-2 border-t border-border pt-4">
              <PermissionGate permission="DOCUMENT_DOWNLOAD">
                <Button variant="outline" onClick={handleDownload}>
                  <Download className="mr-1.5 h-4 w-4" /> Download
                </Button>
              </PermissionGate>
              {document.status !== "ARCHIVED" ? (
                <PermissionGate permission="DOCUMENT_ARCHIVE">
                  <Button variant="outline" onClick={() => setConfirmArchiveOpen(true)}>
                    <Archive className="mr-1.5 h-4 w-4" /> Archive
                  </Button>
                </PermissionGate>
              ) : (
                <PermissionGate permission="DOCUMENT_RESTORE">
                  <Button variant="outline" onClick={handleRestore}>
                    <ArchiveRestore className="mr-1.5 h-4 w-4" /> Restore
                  </Button>
                </PermissionGate>
              )}
            </div>
          </div>
        )}

        <ConfirmDialog
          open={confirmArchiveOpen}
          onOpenChange={setConfirmArchiveOpen}
          title="Archive document"
          description={`"${document?.original_filename}" will be moved to archived status. It stays available to authorized users and can be restored later.`}
          confirmLabel="Archive"
          onConfirm={handleArchive}
        />
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  value,
  mono,
  className,
}: {
  label: string;
  value: string;
  mono?: boolean;
  className?: string;
}) {
  return (
    <div className={className}>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={mono ? "mt-1 break-all font-mono text-xs" : "mt-1"}>{value}</dd>
    </div>
  );
}
