import type { DocumentStatus, DocumentType } from "@/types/api";

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  SALES_INVOICE: "Sales Invoice",
  PURCHASE_INVOICE: "Purchase Invoice",
  EXPENSE_BILL: "Expense Bill",
  BANK_STATEMENT: "Bank Statement",
  GST_REPORT: "GST Report",
  TDS_DOCUMENT: "TDS Document",
  INCOME_TAX_DOCUMENT: "Income Tax Document",
  FINANCIAL_STATEMENT: "Financial Statement",
  OTHER: "Other",
};

export const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  UPLOADED: "Uploaded",
  PROCESSING: "Processing",
  READY: "Ready",
  REVIEW_REQUIRED: "Review Required",
  VERIFIED: "Verified",
  ARCHIVED: "Archived",
  FAILED: "Failed",
};

export const DOCUMENT_STATUS_BADGE_VARIANT: Record<
  DocumentStatus,
  "default" | "secondary" | "destructive" | "success" | "warning" | "outline"
> = {
  UPLOADED: "outline",
  PROCESSING: "warning",
  READY: "success",
  REVIEW_REQUIRED: "warning",
  VERIFIED: "success",
  ARCHIVED: "secondary",
  FAILED: "destructive",
};

export const ACCEPTED_UPLOAD_MIME_BY_EXTENSION: Record<string, string> = {
  pdf: "application/pdf",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  xls: "application/vnd.ms-excel",
  csv: "text/csv",
};

export const ACCEPTED_UPLOAD_EXTENSIONS = Object.keys(ACCEPTED_UPLOAD_MIME_BY_EXTENSION);

export const MAX_UPLOAD_SIZE_MB = 10;
