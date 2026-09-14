import { useRef, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, FileWarning, UploadCloud, X } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useUploadDocument } from "@/hooks/useDocuments";
import { ApiError } from "@/lib/api-client";
import { cn, formatFileSize } from "@/lib/utils";
import { DOCUMENT_TYPES, type DocumentType } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DOCUMENT_TYPE_LABELS, ACCEPTED_UPLOAD_EXTENSIONS, MAX_UPLOAD_SIZE_MB } from "./documentConstants";
import { uploadMetadataSchema, type UploadMetadataValues } from "./uploadSchema";

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type ClientValidationError = { message: string } | null;

function validateFileClientSide(file: File): ClientValidationError {
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!extension || !ACCEPTED_UPLOAD_EXTENSIONS.includes(extension)) {
    return { message: `Unsupported file type. Allowed: ${ACCEPTED_UPLOAD_EXTENSIONS.join(", ")}` };
  }
  if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
    return { message: `File exceeds the ${MAX_UPLOAD_SIZE_MB}MB upload limit` };
  }
  if (file.size === 0) {
    return { message: "File is empty" };
  }
  return null;
}

export function UploadDialog({ open, onOpenChange }: UploadDialogProps) {
  const { activeCompany } = useAuth();
  const uploadMutation = useUploadDocument(activeCompany?.company_id ?? "");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [serverError, setServerError] = useState<{ message: string; isDuplicate: boolean } | null>(
    null
  );
  const [success, setSuccess] = useState(false);

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<UploadMetadataValues>({ resolver: zodResolver(uploadMetadataSchema) });

  const resetAll = () => {
    setFile(null);
    setFileError(null);
    setServerError(null);
    setSuccess(false);
    reset({ document_type: undefined, description: "" });
  };

  const handleOpenChange = (next: boolean) => {
    if (next) resetAll();
    onOpenChange(next);
  };

  const handleFileSelected = (selected: File | null) => {
    setServerError(null);
    if (!selected) {
      setFile(null);
      return;
    }
    const error = validateFileClientSide(selected);
    if (error) {
      setFile(null);
      setFileError(error.message);
      return;
    }
    setFileError(null);
    setFile(selected);
  };

  const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const dropped = event.dataTransfer.files?.[0] ?? null;
    handleFileSelected(dropped);
  };

  const submit = async (values: UploadMetadataValues) => {
    if (!file || !activeCompany) return;
    setServerError(null);
    try {
      await uploadMutation.mutateAsync({
        companyId: activeCompany.company_id,
        file,
        documentType: values.document_type as DocumentType,
        description: values.description || undefined,
      });
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError({
          message: err.message,
          isDuplicate: err.code === "DOCUMENT_DUPLICATE",
        });
      } else {
        setServerError({ message: "Something went wrong. Try again.", isDuplicate: false });
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload document</DialogTitle>
          <DialogDescription>
            Add a document to {activeCompany?.company_name ?? "this company"}. Supported types:{" "}
            {ACCEPTED_UPLOAD_EXTENSIONS.join(", ").toUpperCase()} · up to {MAX_UPLOAD_SIZE_MB}MB.
          </DialogDescription>
        </DialogHeader>

        {success ? (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <CheckCircle2 className="h-10 w-10 text-success" />
            <p className="font-medium">Document uploaded successfully</p>
            <Button onClick={() => handleOpenChange(false)}>Done</Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit(submit)} className="space-y-4">
            {serverError && (
              <Alert variant="destructive">
                <FileWarning className="h-4 w-4" />
                <AlertDescription>
                  {serverError.isDuplicate
                    ? "An identical document already exists in this company."
                    : serverError.message}
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-1.5">
              <Label>File</Label>
              <div
                role="button"
                tabIndex={0}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={onDrop}
                className={cn(
                  "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed px-4 py-8 text-center transition-colors",
                  isDragging ? "border-primary bg-primary/5" : "border-border hover:bg-accent",
                  fileError && "border-destructive/50"
                )}
              >
                <UploadCloud className="h-8 w-8 text-muted-foreground" />
                {file ? (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium">{file.name}</span>
                    <span className="text-muted-foreground">({formatFileSize(file.size)})</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleFileSelected(null);
                      }}
                      className="text-muted-foreground hover:text-destructive"
                      aria-label="Remove file"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <>
                    <p className="text-sm">
                      <span className="font-medium text-primary">Click to upload</span> or drag and drop
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {ACCEPTED_UPLOAD_EXTENSIONS.join(", ").toUpperCase()} up to {MAX_UPLOAD_SIZE_MB}MB
                    </p>
                  </>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept={ACCEPTED_UPLOAD_EXTENSIONS.map((e) => `.${e}`).join(",")}
                  onChange={(e) => handleFileSelected(e.target.files?.[0] ?? null)}
                />
              </div>
              {fileError && <p className="text-xs text-destructive">{fileError}</p>}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="document_type">Document type</Label>
              <Controller
                control={control}
                name="document_type"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="document_type">
                      <SelectValue placeholder="Select a document type" />
                    </SelectTrigger>
                    <SelectContent>
                      {DOCUMENT_TYPES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {DOCUMENT_TYPE_LABELS[type]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.document_type && (
                <p className="text-xs text-destructive">{errors.document_type.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="description">Description (optional)</Label>
              <textarea
                id="description"
                rows={3}
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                placeholder="Add any helpful context about this document…"
                {...register("description")}
              />
              {errors.description && (
                <p className="text-xs text-destructive">{errors.description.message}</p>
              )}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={!file || isSubmitting}>
                {isSubmitting ? "Uploading…" : "Upload document"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
