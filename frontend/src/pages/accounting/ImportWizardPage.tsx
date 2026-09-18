import { useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, UploadCloud, XCircle } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import { useBankStatements } from "@/hooks/useBankStatements";
import { useGstReturnPeriods } from "@/hooks/useGstReturnPeriods";
import { useCommitImportJob, useImportFields, useImportErrors, useImportPreview } from "@/hooks/useImports";
import { importService } from "@/services/importService";
import { documentService } from "@/services/documentService";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";
import type { ImportType } from "@/types/accounting";

const IMPORT_TYPES: {
  value: ImportType;
  label: string;
  needsFinancialYear: boolean;
  needsReturnPeriod?: boolean;
  needsBankStatement?: boolean;
}[] = [
  { value: "CUSTOMERS", label: "Customers", needsFinancialYear: false },
  { value: "VENDORS", label: "Vendors", needsFinancialYear: false },
  { value: "PRODUCTS", label: "Products / Services", needsFinancialYear: false },
  { value: "LEDGERS", label: "Ledgers", needsFinancialYear: false },
  { value: "SALES", label: "Sales Invoices", needsFinancialYear: true },
  { value: "PURCHASES", label: "Purchase Invoices", needsFinancialYear: true },
  { value: "PAYMENTS", label: "Payments", needsFinancialYear: true },
  { value: "RECEIPTS", label: "Receipts", needsFinancialYear: true },
  { value: "JOURNALS", label: "Journal Entries", needsFinancialYear: true },
  { value: "TALLY", label: "Tally Export (CSV/XLSX)", needsFinancialYear: true },
  { value: "GSTR2B", label: "GSTR-2B (CSV/XLSX/JSON)", needsFinancialYear: false, needsReturnPeriod: true },
  { value: "TDS", label: "TDS Reconciliation Data (CSV/XLSX)", needsFinancialYear: false },
  { value: "BANK_STATEMENT", label: "Bank Statement (CSV/XLSX)", needsFinancialYear: false, needsBankStatement: true },
];

type WizardStep = "setup" | "mapping" | "result";

export default function ImportWizardPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const companyId = activeCompany?.company_id ?? "";
  const fileInputRef = useRef<HTMLInputElement>(null);

  const presetImportType = searchParams.get("importType") as ImportType | null;
  const presetReturnPeriodId = searchParams.get("returnPeriodId");
  const presetBankStatementId = searchParams.get("bankStatementId");

  const [step, setStep] = useState<WizardStep>("setup");
  const [importType, setImportType] = useState<ImportType | "">(presetImportType ?? "");
  const [financialYearId, setFinancialYearId] = useState<string>("");
  const [returnPeriodId, setReturnPeriodId] = useState<string>(presetReturnPeriodId ?? "");
  const [bankStatementId, setBankStatementId] = useState<string>(presetBankStatementId ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [sampleRows, setSampleRows] = useState<Record<string, string>[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [jobId, setJobId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: financialYears } = useFinancialYears(companyId);
  const { data: returnPeriods } = useGstReturnPeriods(companyId);
  const { data: bankStatements } = useBankStatements(companyId);
  const { data: fieldDefs } = useImportFields((importType || null) as ImportType | null);
  const commitMutation = useCommitImportJob(companyId);
  const { data: jobPreview } = useImportPreview(companyId, jobId ?? undefined);
  const { data: jobErrors } = useImportErrors(companyId, jobId ?? undefined);

  const selectedType = IMPORT_TYPES.find((t) => t.value === importType);

  const handleUploadAndDetectColumns = async () => {
    if (!file || !importType) return;
    setError(null);
    setIsUploading(true);
    try {
      const doc = await documentService.upload({
        companyId,
        file,
        documentType: importType === "GSTR2B" ? "GST_REPORT" : "OTHER",
      });
      setDocumentId(doc.id);
      const preview = await importService.previewColumns(companyId, doc.id, importType);
      setColumns(preview.columns);
      setSampleRows(preview.sample_rows);
      setStep("mapping");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not read this file");
    } finally {
      setIsUploading(false);
    }
  };

  const handleCreateJob = async () => {
    if (!documentId || !importType) return;
    setError(null);
    try {
      const job = await importService.create(companyId, {
        document_id: documentId,
        import_type: importType,
        financial_year_id: financialYearId || undefined,
        return_period_id: returnPeriodId || undefined,
        bank_statement_id: bankStatementId || undefined,
        column_mapping: mapping,
      });
      setJobId(job.id);
      setStep("result");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not process this import");
    }
  };

  const handleCommit = async () => {
    if (!jobId) return;
    try {
      await commitMutation.mutateAsync(jobId);
      toast({ title: "Import committed", variant: "success" });
      navigate(`/accounting/imports/${jobId}`);
    } catch (err) {
      toast({ title: "Commit failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  if (!activeCompany) return null;

  const requiredFieldsMapped = (fieldDefs ?? [])
    .filter((f) => f.required)
    .every((f) => Object.values(mapping).includes(f.name));

  return (
    <div className="max-w-3xl space-y-6">
      <Link to="/accounting/imports" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to imports
      </Link>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New import</h1>
        <p className="text-sm text-muted-foreground">Upload a CSV, Excel, or Tally export and map its columns to Tally Tax fields.</p>
      </div>

      <StepIndicator step={step} />

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {step === "setup" && (
        <Card>
          <CardHeader>
            <CardTitle>1. Select type &amp; upload file</CardTitle>
            <CardDescription>Not every file has the same column names — that's mapped in the next step.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Import type</Label>
              <Select value={importType} onValueChange={(v) => setImportType(v as ImportType)}>
                <SelectTrigger><SelectValue placeholder="Select what you're importing" /></SelectTrigger>
                <SelectContent>
                  {IMPORT_TYPES.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            {selectedType?.needsFinancialYear && (
              <div className="space-y-1.5">
                <Label>Financial year</Label>
                <Select value={financialYearId} onValueChange={setFinancialYearId}>
                  <SelectTrigger><SelectValue placeholder="Select financial year" /></SelectTrigger>
                  <SelectContent>
                    {(financialYears?.items ?? []).map((fy) => <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}

            {selectedType?.needsReturnPeriod && (
              <div className="space-y-1.5">
                <Label>GST return period</Label>
                <Select value={returnPeriodId} onValueChange={setReturnPeriodId}>
                  <SelectTrigger><SelectValue placeholder="Select return period" /></SelectTrigger>
                  <SelectContent>
                    {(returnPeriods?.items ?? []).map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.month}/{p.year}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {selectedType?.needsBankStatement && (
              <div className="space-y-1.5">
                <Label>Bank statement</Label>
                <Select value={bankStatementId} onValueChange={setBankStatementId}>
                  <SelectTrigger><SelectValue placeholder="Select a registered statement" /></SelectTrigger>
                  <SelectContent>
                    {(bankStatements?.items ?? []).map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.statement_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Register the statement first under Banking → Statements, then import its transactions here.
                </p>
              </div>
            )}

            <div className="space-y-1.5">
              <Label>File</Label>
              <div
                role="button"
                tabIndex={0}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed border-border px-4 py-8 text-center transition-colors hover:bg-accent"
                )}
              >
                <UploadCloud className="h-8 w-8 text-muted-foreground" />
                {file ? (
                  <p className="text-sm font-medium">{file.name}</p>
                ) : (
                  <p className="text-sm">
                    <span className="font-medium text-primary">Click to upload</span>
                    {importType === "GSTR2B" ? " — CSV, XLSX, or JSON" : " — CSV, XLSX, or XLS"}
                  </p>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={importType === "GSTR2B" ? ".csv,.xlsx,.xls,.json" : ".csv,.xlsx,.xls"}
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                disabled={
                  !file ||
                  !importType ||
                  (selectedType?.needsFinancialYear && !financialYearId) ||
                  (selectedType?.needsReturnPeriod && !returnPeriodId) ||
                  (selectedType?.needsBankStatement && !bankStatementId) ||
                  isUploading
                }
                onClick={handleUploadAndDetectColumns}
              >
                {isUploading ? "Reading file…" : "Continue"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === "mapping" && (
        <Card>
          <CardHeader>
            <CardTitle>2. Map columns</CardTitle>
            <CardDescription>Match each column from your file to a Tally Tax field. Required fields are marked *.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {columns.map((column) => (
                <div key={column} className="flex items-center gap-3">
                  <div className="w-1/2 truncate text-sm font-medium" title={column}>{column}</div>
                  <Select
                    value={mapping[column] ?? "__skip__"}
                    onValueChange={(value) =>
                      setMapping((prev) => {
                        const next = { ...prev };
                        if (value === "__skip__") delete next[column];
                        else next[column] = value;
                        return next;
                      })
                    }
                  >
                    <SelectTrigger className="w-1/2"><SelectValue placeholder="Don't import" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__skip__">Don't import</SelectItem>
                      {(fieldDefs ?? []).map((f) => (
                        <SelectItem key={f.name} value={f.name}>{f.label}{f.required ? " *" : ""}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </div>

            {sampleRows.length > 0 && (
              <div className="rounded-md border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>{columns.map((c) => <TableHead key={c}>{c}</TableHead>)}</TableRow>
                  </TableHeader>
                  <TableBody>
                    {sampleRows.slice(0, 3).map((row, i) => (
                      <TableRow key={i}>{columns.map((c) => <TableCell key={c} className="text-xs text-muted-foreground">{row[c]}</TableCell>)}</TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {!requiredFieldsMapped && (
              <p className="text-xs text-destructive">Map all required fields before continuing.</p>
            )}

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep("setup")}>Back</Button>
              <Button disabled={!requiredFieldsMapped} onClick={handleCreateJob}>Preview import</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === "result" && jobId && (
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>3. Preview &amp; commit</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {!jobPreview ? (
                <Skeleton className="h-32 w-full" />
              ) : (
                <>
                  <div className="grid grid-cols-3 gap-3 text-center text-sm">
                    <div className="rounded-md border border-border p-3">
                      <p className="text-2xl font-semibold">{jobPreview.pagination.total}</p>
                      <p className="text-xs text-muted-foreground">Total rows</p>
                    </div>
                    <div className="rounded-md border border-border p-3">
                      <p className="text-2xl font-semibold text-success">
                        {jobPreview.items.filter((r) => r.status === "VALID").length}
                      </p>
                      <p className="text-xs text-muted-foreground">Valid (this page)</p>
                    </div>
                    <div className="rounded-md border border-border p-3">
                      <p className="text-2xl font-semibold text-destructive">{jobErrors?.pagination.total ?? 0}</p>
                      <p className="text-xs text-muted-foreground">Errors</p>
                    </div>
                  </div>

                  <div className="max-h-80 overflow-y-auto rounded-md border border-border">
                    <Table>
                      <TableHeader>
                        <TableRow><TableHead>Row</TableHead><TableHead>Status</TableHead><TableHead>Detail</TableHead></TableRow>
                      </TableHeader>
                      <TableBody>
                        {jobPreview.items.map((row) => (
                          <TableRow key={row.id}>
                            <TableCell>{row.row_number}</TableCell>
                            <TableCell>
                              <Badge variant={row.status === "VALID" ? "success" : row.status === "DUPLICATE" ? "warning" : "destructive"}>
                                {row.status}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {row.normalized_data ? Object.values(row.normalized_data)[0]?.toString() : "—"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {jobErrors && jobErrors.items.length > 0 && (
                    <div className="space-y-2">
                      <p className="flex items-center gap-1.5 text-sm font-medium text-destructive">
                        <XCircle className="h-4 w-4" /> Errors
                      </p>
                      <div className="max-h-48 overflow-y-auto rounded-md border border-destructive/30">
                        <Table>
                          <TableHeader>
                            <TableRow><TableHead>Row</TableHead><TableHead>Field</TableHead><TableHead>Error</TableHead></TableRow>
                          </TableHeader>
                          <TableBody>
                            {jobErrors.items.map((e) => (
                              <TableRow key={e.id}>
                                <TableCell>{e.row_number}</TableCell>
                                <TableCell className="text-muted-foreground">{e.field_name ?? "—"}</TableCell>
                                <TableCell className="text-xs">{e.error_message}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  )}

                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => navigate("/accounting/imports")}>Do this later</Button>
                    <Button onClick={handleCommit} disabled={commitMutation.isPending}>
                      <CheckCircle2 className="mr-1.5 h-4 w-4" />
                      {commitMutation.isPending ? "Committing…" : "Commit import"}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function StepIndicator({ step }: { step: WizardStep }) {
  const steps: { key: WizardStep; label: string }[] = [
    { key: "setup", label: "Upload" },
    { key: "mapping", label: "Map columns" },
    { key: "result", label: "Preview & commit" },
  ];
  const currentIndex = steps.findIndex((s) => s.key === step);
  return (
    <div className="flex items-center gap-2 text-xs">
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center gap-2">
          <span
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-full border text-xs font-medium",
              i <= currentIndex ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground"
            )}
          >
            {i + 1}
          </span>
          <span className={i <= currentIndex ? "font-medium" : "text-muted-foreground"}>{s.label}</span>
          {i < steps.length - 1 && <span className="mx-2 h-px w-8 bg-border" />}
        </div>
      ))}
    </div>
  );
}
