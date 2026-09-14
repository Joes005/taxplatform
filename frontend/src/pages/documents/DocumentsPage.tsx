import { useState } from "react";
import { FileText, MoreHorizontal, Plus, Search } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useArchiveDocument, useDocuments, useRestoreDocument } from "@/hooks/useDocuments";
import { documentService } from "@/services/documentService";
import { PermissionGate } from "@/components/PermissionGate";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDateTime, formatFileSize, triggerBlobDownload } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";
import type { Document, DocumentStatus, DocumentType } from "@/types/api";
import {
  DOCUMENT_STATUS_BADGE_VARIANT,
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_TYPE_LABELS,
} from "./documentConstants";
import { UploadDialog } from "./UploadDialog";
import { DocumentDetailsDialog } from "./DocumentDetailsDialog";

export default function DocumentsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id;

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [archivingDocument, setArchivingDocument] = useState<Document | null>(null);

  const { data, isLoading } = useDocuments(
    companyId
      ? {
          companyId,
          page,
          pageSize: 20,
          search: search || undefined,
          documentType: (typeFilter || undefined) as DocumentType | undefined,
          status: (statusFilter || undefined) as DocumentStatus | undefined,
          dateFrom: dateFrom || undefined,
          dateTo: dateTo || undefined,
        }
      : null
  );

  const archiveMutation = useArchiveDocument(companyId ?? "");
  const restoreMutation = useRestoreDocument(companyId ?? "");

  if (!activeCompany) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-24 text-center">
        <FileText className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm font-medium">No active company selected</p>
        <p className="text-xs text-muted-foreground">
          Choose a company from the switcher above to manage its documents.
        </p>
      </div>
    );
  }

  const handleDownload = async (doc: Document) => {
    if (!companyId) return;
    try {
      const { blob, filename } = await documentService.download(companyId, doc.id);
      triggerBlobDownload(blob, filename ?? doc.original_filename);
    } catch (err) {
      toast({
        title: "Download failed",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "destructive",
      });
    }
  };

  const handleConfirmArchive = async () => {
    if (!archivingDocument) return;
    await archiveMutation.mutateAsync(archivingDocument.id);
    toast({ title: "Document archived", variant: "success" });
  };

  const handleRestore = async (doc: Document) => {
    try {
      await restoreMutation.mutateAsync(doc.id);
      toast({ title: "Document restored", variant: "success" });
    } catch (err) {
      toast({
        title: "Could not restore document",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "destructive",
      });
    }
  };

  const hasFilters = search || typeFilter || statusFilter || dateFrom || dateTo;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Manage evidence and compliance documents for {activeCompany.company_name}
          </p>
        </div>
        <PermissionGate permission="DOCUMENT_UPLOAD">
          <Button onClick={() => setUploadOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" />
            Upload document
          </Button>
        </PermissionGate>
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-white p-4">
        <div className="min-w-[14rem] flex-1 space-y-1.5">
          <Label htmlFor="doc-search" className="text-xs">
            Search
          </Label>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              id="doc-search"
              placeholder="Filename, description, type…"
              className="pl-8"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="type-filter" className="text-xs">
            Type
          </Label>
          <select
            id="type-filter"
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">All types</option>
            {Object.entries(DOCUMENT_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="status-filter" className="text-xs">
            Status
          </Label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">All statuses</option>
            {Object.entries(DOCUMENT_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="date-from" className="text-xs">
            From
          </Label>
          <Input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="date-to" className="text-xs">
            To
          </Label>
          <Input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
          />
        </div>

        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearch("");
              setTypeFilter("");
              setStatusFilter("");
              setDateFrom("");
              setDateTo("");
              setPage(1);
            }}
          >
            Clear filters
          </Button>
        )}
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>File</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Uploaded By</TableHead>
                <TableHead>Uploaded At</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>
                    <button
                      onClick={() => setSelectedDocumentId(doc.id)}
                      className="flex items-center gap-2 text-left font-medium text-primary hover:underline"
                    >
                      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="max-w-xs truncate">{doc.original_filename}</span>
                    </button>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {DOCUMENT_TYPE_LABELS[doc.document_type]}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatFileSize(doc.file_size)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={DOCUMENT_STATUS_BADGE_VARIANT[doc.status]}>
                      {DOCUMENT_STATUS_LABELS[doc.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {doc.uploaded_by.first_name} {doc.uploaded_by.last_name}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatDateTime(doc.uploaded_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => setSelectedDocumentId(doc.id)}>
                          View
                        </DropdownMenuItem>
                        <PermissionGate permission="DOCUMENT_DOWNLOAD">
                          <DropdownMenuItem onClick={() => handleDownload(doc)}>
                            Download
                          </DropdownMenuItem>
                        </PermissionGate>
                        {doc.status !== "ARCHIVED" ? (
                          <PermissionGate permission="DOCUMENT_ARCHIVE">
                            <DropdownMenuItem onClick={() => setArchivingDocument(doc)}>
                              Archive
                            </DropdownMenuItem>
                          </PermissionGate>
                        ) : (
                          <PermissionGate permission="DOCUMENT_RESTORE">
                            <DropdownMenuItem onClick={() => handleRestore(doc)}>
                              Restore
                            </DropdownMenuItem>
                          </PermissionGate>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
            <FileText className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium">No documents uploaded yet</p>
            <p className="text-xs text-muted-foreground">
              {hasFilters ? "Try adjusting your filters." : "Upload your first document to get started."}
            </p>
          </div>
        )}
      </div>

      {data && data.pagination.total_pages > 1 && (
        <div className="flex items-center justify-end gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="text-xs text-muted-foreground">
            Page {data.pagination.page} of {data.pagination.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.pagination.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}

      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} />
      <DocumentDetailsDialog
        documentId={selectedDocumentId}
        onOpenChange={(open) => !open && setSelectedDocumentId(null)}
      />
      <ConfirmDialog
        open={!!archivingDocument}
        onOpenChange={(open) => !open && setArchivingDocument(null)}
        title="Archive document"
        description={`"${archivingDocument?.original_filename}" will be moved to archived status. It stays available to authorized users and can be restored later.`}
        confirmLabel="Archive"
        onConfirm={handleConfirmArchive}
      />
    </div>
  );
}
