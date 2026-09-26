import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  Layers,
  RefreshCw,
  Sparkles,
  Trash2,
  UploadCloud,
} from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import { documentService } from "@/services/documentService";
import {
  FileInspectionResult,
  TallyCommitResponse,
  TallyExportPreview,
  TallyMappingRule,
  TallyMappingTemplate,
  TallyPreviewData,
  tallyService,
} from "@/services/tallyService";
import { ledgerService } from "@/services/accountingMasterDataService";
import type { FinancialYear, Ledger } from "@/types/accounting";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyCompanyState } from "./LedgersPage";

export default function TallyCenterPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: financialYears } = useFinancialYears(companyId);

  // Active Tab
  const [activeTab, setActiveTab] = useState<string>("import");

  // Import State
  const [importFile, setImportFile] = useState<File | null>(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectResult, setDetectResult] = useState<FileInspectionResult | null>(null);
  const [uploadedDocId, setUploadedDocId] = useState<string | null>(null);

  // Preview & Mapping State
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [selectedFyId, setSelectedFyId] = useState<string>("");
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewData, setPreviewData] = useState<TallyPreviewData | null>(null);
  const [confirmedMappings, setConfirmedMappings] = useState<TallyMappingRule[]>([]);
  const [saveTemplateName, setSaveTemplateName] = useState<string>("");

  // Existing Ledgers for dropdown mapping
  const [availableLedgers, setAvailableLedgers] = useState<{ id: string; name: string; type: string }[]>([]);

  // Commit State
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState<TallyCommitResponse | null>(null);

  // Templates Tab State
  const [templates, setTemplates] = useState<TallyMappingTemplate[]>([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);

  // Export Tab State
  const [exportFormat, setExportFormat] = useState<"XML" | "CSV" | "XLSX">("XML");
  const [exportFyId, setExportFyId] = useState<string>("");
  const [exportStartDate, setExportStartDate] = useState<string>("");
  const [exportEndDate, setExportEndDate] = useState<string>("");
  const [selectedVoucherTypes, setSelectedVoucherTypes] = useState<string[]>([
    "SALES",
    "PURCHASE",
    "RECEIPT",
    "PAYMENT",
    "JOURNAL",
  ]);
  const [exportPreview, setExportPreview] = useState<TallyExportPreview | null>(null);
  const [isPreviewingExport, setIsPreviewingExport] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Load Templates & Ledgers
  const loadTemplates = useCallback(async () => {
    if (!companyId) return;
    setIsLoadingTemplates(true);
    try {
      const data = await tallyService.listTemplates(companyId);
      setTemplates(data || []);
    } catch {
      // ignore
    } finally {
      setIsLoadingTemplates(false);
    }
  }, [companyId]);

  const loadLedgers = useCallback(async () => {
    if (!companyId) return;
    try {
      const res = await ledgerService.list(companyId, 1, 100);
      setAvailableLedgers(res.items.map((l: Ledger) => ({ id: l.id, name: l.name, type: l.ledger_type })));
    } catch {
      // ignore
    }
  }, [companyId]);

  useEffect(() => {
    if (companyId) {
      loadTemplates();
      loadLedgers();
    }
  }, [companyId, loadTemplates, loadLedgers]);

  if (!activeCompany) return <EmptyCompanyState icon={FileSpreadsheet} />;

  // 1. Handle File Select & Upload
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImportFile(file);
    setDetectResult(null);
    setPreviewData(null);
    setCommitResult(null);
    setIsDetecting(true);

    try {
      const doc = await documentService.upload({
        companyId,
        file,
        documentType: "OTHER",
      });
      setUploadedDocId(doc.id);

      const inspection = await tallyService.detectFile(companyId, doc.id);
      setDetectResult(inspection);

      toast({
        title: "File Ingested",
        description: `Format: ${inspection.detected_format} (${(inspection.size_bytes / 1024).toFixed(1)} KB)`,
        variant: "success",
      });
    } catch (err: unknown) {
      toast({
        title: "File Ingestion Failed",
        description: err instanceof Error ? err.message : "Failed to parse uploaded file",
        variant: "destructive",
      });
    } finally {
      setIsDetecting(false);
    }
  };

  // 2. Run Intelligent Validation Preview
  const handleRunPreview = async () => {
    if (!uploadedDocId) return;
    setIsPreviewing(true);
    setCommitResult(null);

    try {
      const data = await tallyService.preview(companyId, {
        document_id: uploadedDocId,
        template_id: selectedTemplateId || undefined,
        financial_year_id: selectedFyId || undefined,
      });
      setPreviewData(data);
      setConfirmedMappings(data.mappings);

      toast({
        title: "Validation Preview Generated",
        description: `${data.valid_records} valid records, ${data.duplicate_records} duplicates found.`,
      });
    } catch (err: unknown) {
      toast({
        title: "Preview Failed",
        description: err instanceof Error ? err.message : "Could not validate Tally export file",
        variant: "destructive",
      });
    } finally {
      setIsPreviewing(false);
    }
  };

  // 3. Update Mapping Rule
  const handleUpdateMappingTarget = (index: number, targetId: string) => {
    const updated = [...confirmedMappings];
    const rule = updated[index];
    const target = availableLedgers.find((l) => l.id === targetId);
    if (target) {
      rule.target_id = target.id;
      rule.target_name = target.name;
      rule.status = "MANUAL";
      rule.confidence = 1.0;
    } else {
      rule.target_id = null;
      rule.target_name = null;
      rule.status = "UNMAPPED";
      rule.confidence = 0.0;
    }
    setConfirmedMappings(updated);
  };

  // 4. Commit to Accounting
  const handleCommit = async () => {
    if (!previewData) return;
    setIsCommitting(true);

    try {
      const res = await tallyService.commit(companyId, {
        job_id: previewData.job_id,
        confirmed_mappings: confirmedMappings,
        save_as_template_name: saveTemplateName.trim() || undefined,
      });
      setCommitResult(res);
      toast({
        title: "Import Committed Successfully!",
        description: `Imported ${res.successful_rows} vouchers into accounting ledgers.`,
        variant: "success",
      });
      loadTemplates();
    } catch (err: unknown) {
      toast({
        title: "Commit Failed",
        description: err instanceof Error ? err.message : "An error occurred during atomic commit",
        variant: "destructive",
      });
    } finally {
      setIsCommitting(false);
    }
  };

  // 5. Handle Export Preview
  const handlePreviewExport = async () => {
    setIsPreviewingExport(true);
    try {
      const data = await tallyService.previewExport(companyId, {
        financial_year_id: exportFyId || undefined,
        start_date: exportStartDate || undefined,
        end_date: exportEndDate || undefined,
        voucher_types: selectedVoucherTypes,
      });
      setExportPreview(data);
    } catch (err: unknown) {
      toast({
        title: "Export Preview Failed",
        description: err instanceof Error ? err.message : "Failed to calculate export stats",
        variant: "destructive",
      });
    } finally {
      setIsPreviewingExport(false);
    }
  };

  // 6. Download Export File
  const handleDownloadExport = async () => {
    setIsExporting(true);
    try {
      const blob = await tallyService.exportData(companyId, {
        format: exportFormat,
        financial_year_id: exportFyId || undefined,
        start_date: exportStartDate || undefined,
        end_date: exportEndDate || undefined,
        voucher_types: selectedVoucherTypes,
      });

      const ext = exportFormat === "XML" ? "xml" : exportFormat === "CSV" ? "csv" : "xlsx";
      const filename = `tally_${exportFormat.toLowerCase()}_export_${new Date().toISOString().slice(0, 10)}.${ext}`;

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: "Export Complete",
        description: `Downloaded ${filename}`,
        variant: "success",
      });
    } catch (err: unknown) {
      toast({
        title: "Export Failed",
        description: err instanceof Error ? err.message : "Failed to download export file",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  // 7. Delete Template
  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm("Are you sure you want to delete this mapping template?")) return;
    try {
      await tallyService.deleteTemplate(companyId, templateId);
      toast({ title: "Template Deleted", variant: "success" });
      loadTemplates();
    } catch (err: unknown) {
      toast({ title: "Delete Failed", description: err instanceof Error ? err.message : "Failed to delete template", variant: "destructive" });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Tally Bridge & Compatibility</h1>
            <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20">
              Phase 12
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Ingest, normalize, map, validate, and commit Tally Prime & ERP 9 data with automated reconciliation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to="/accounting/imports">
              <Layers className="mr-1.5 h-4 w-4" /> All Imports
            </Link>
          </Button>
          <Button variant="outline" size="sm" onClick={() => loadTemplates()}>
            <RefreshCw className="mr-1.5 h-4 w-4" /> Refresh
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-3 max-w-lg">
          <TabsTrigger value="import" className="flex items-center gap-2">
            <UploadCloud className="h-4 w-4" /> Import & Reconcile
          </TabsTrigger>
          <TabsTrigger value="export" className="flex items-center gap-2">
            <Download className="h-4 w-4" /> Export Studio
          </TabsTrigger>
          <TabsTrigger value="templates" className="flex items-center gap-2">
            <BookOpen className="h-4 w-4" /> Mapping Templates ({templates.length})
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: IMPORT & RECONCILE */}
        <TabsContent value="import" className="space-y-6">
          {/* Step 1: File Ingestion */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileCode className="h-5 w-5 text-primary" /> 1. Upload & Format Detection
              </CardTitle>
              <CardDescription>
                Upload Tally XML (Daybook/Masters envelope), CSV exports, or Excel multi-sheet workbooks.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                onClick={() => fileInputRef.current?.click()}
                className="flex flex-col items-center justify-center border-2 border-dashed border-border rounded-xl p-8 cursor-pointer hover:border-primary/60 hover:bg-muted/40 transition-colors"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xml,.csv,.xlsx,.xls"
                  className="hidden"
                  onChange={handleFileSelect}
                />
                <UploadCloud className="h-10 w-10 text-muted-foreground mb-3" />
                <p className="text-sm font-medium text-foreground">
                  {importFile ? importFile.name : "Click or drag & drop Tally export file"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Supports Tally XML (&lt;ENVELOPE&gt;), Daybook CSV, or Register Excel (.xlsx) up to 50MB
                </p>
              </div>

              {isDetecting && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground p-3 bg-muted/40 rounded-lg">
                  <RefreshCw className="h-4 w-4 animate-spin text-primary" /> Inspecting file signature and encoding...
                </div>
              )}

              {detectResult && (
                <div className="rounded-xl border border-border bg-card p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                      <span className="font-semibold text-sm">Detected Format:</span>
                      <Badge variant="secondary" className="font-mono">
                        {detectResult.detected_format}
                      </Badge>
                      <Badge variant="outline">{detectResult.encoding.toUpperCase()}</Badge>
                      {detectResult.company_name && (
                        <span className="text-xs text-muted-foreground">
                          Company in File: <strong>{detectResult.company_name}</strong>
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {(detectResult.size_bytes / 1024).toFixed(1)} KB
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-border">
                    <div className="flex-1 min-w-[200px]">
                      <Label className="text-xs">Saved Mapping Template (Optional)</Label>
                      <Select value={selectedTemplateId} onValueChange={setSelectedTemplateId}>
                        <SelectTrigger className="h-9 mt-1">
                          <SelectValue placeholder="Auto-map or select template" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">Auto-match (None)</SelectItem>
                          {templates.map((tpl) => (
                            <SelectItem key={tpl.id} value={tpl.id}>
                              {tpl.name} ({tpl.rules?.length || 0} rules)
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="flex-1 min-w-[200px]">
                      <Label className="text-xs">Financial Year</Label>
                      <Select value={selectedFyId} onValueChange={setSelectedFyId}>
                        <SelectTrigger className="h-9 mt-1">
                          <SelectValue placeholder="Auto-detect from voucher dates" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">Auto-resolve from voucher dates</SelectItem>
                          {financialYears?.items?.map((fy: FinancialYear) => (
                            <SelectItem key={fy.id} value={fy.id}>
                              {fy.name} ({fy.start_date} to {fy.end_date})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="pt-5">
                      <Button onClick={handleRunPreview} disabled={isPreviewing} className="gap-2">
                        {isPreviewing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                        Run Intelligent Preview
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Step 2: Validation & Intelligent Preview */}
          {previewData && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-amber-500" /> 2. Validation & Duplicate Detection Preview
                  </div>
                  <Badge variant="outline">Job: {previewData.job_id.slice(0, 8)}</Badge>
                </CardTitle>
                <CardDescription>
                  Review parsed vouchers, duplicate detections, tax calculations, and double-entry balance before committing.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div className="rounded-xl border border-border p-3.5 bg-card">
                    <p className="text-xs text-muted-foreground">Total Vouchers</p>
                    <p className="text-2xl font-bold mt-1 text-foreground">{previewData.total_records}</p>
                  </div>
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3.5">
                    <p className="text-xs text-emerald-700 dark:text-emerald-400">Valid to Commit</p>
                    <p className="text-2xl font-bold mt-1 text-emerald-700 dark:text-emerald-400">
                      {previewData.valid_records}
                    </p>
                  </div>
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3.5">
                    <p className="text-xs text-amber-700 dark:text-amber-400">Duplicates Detected</p>
                    <p className="text-2xl font-bold mt-1 text-amber-700 dark:text-amber-400">
                      {previewData.duplicate_records}
                    </p>
                  </div>
                  <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-3.5">
                    <p className="text-xs text-rose-700 dark:text-rose-400">Errors</p>
                    <p className="text-2xl font-bold mt-1 text-rose-700 dark:text-rose-400">
                      {previewData.error_records}
                    </p>
                  </div>
                  <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-3.5">
                    <p className="text-xs text-blue-700 dark:text-blue-400">Mapping Rules</p>
                    <p className="text-2xl font-bold mt-1 text-blue-700 dark:text-blue-400">
                      {previewData.mappings.length}
                    </p>
                  </div>
                </div>

                {/* Warnings / Errors Alert */}
                {previewData.errors.length > 0 && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Validation Notices ({previewData.errors.length})</AlertTitle>
                    <AlertDescription className="text-xs space-y-1 mt-1">
                      {previewData.errors.slice(0, 5).map((err, idx) => (
                        <p key={idx}>
                          • [{err.code}] {err.message} (Row/Ref: {err.row_ref})
                        </p>
                      ))}
                      {previewData.errors.length > 5 && (
                        <p className="text-muted-foreground italic">
                          ... and {previewData.errors.length - 5} more issues.
                        </p>
                      )}
                    </AlertDescription>
                  </Alert>
                )}

                {/* Interactive Ledger & Party Mapping */}
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Layers className="h-4 w-4 text-primary" /> Ledger & Party Mapping
                  </h3>
                  <div className="rounded-lg border border-border overflow-hidden max-h-64 overflow-y-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Source Type</TableHead>
                          <TableHead>Tally Name</TableHead>
                          <TableHead>Match Status</TableHead>
                          <TableHead>Target Ledger / Account</TableHead>
                          <TableHead className="text-right">Confidence</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {confirmedMappings.map((rule, idx) => (
                          <TableRow key={idx}>
                            <TableCell>
                              <Badge variant="outline">{rule.source_type}</Badge>
                            </TableCell>
                            <TableCell className="font-medium text-foreground">
                              {rule.source_name}
                              {rule.source_group && (
                                <span className="text-xs text-muted-foreground block">{rule.source_group}</span>
                              )}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant={
                                  rule.status === "EXACT" || rule.status === "CONFIRMED"
                                    ? "success"
                                    : rule.status === "PROPOSED"
                                    ? "warning"
                                    : "secondary"
                                }
                              >
                                {rule.status}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {rule.source_type === "LEDGER" ? (
                                <Select
                                  value={rule.target_id || ""}
                                  onValueChange={(val) => handleUpdateMappingTarget(idx, val)}
                                >
                                  <SelectTrigger className="h-8 text-xs w-56">
                                    <SelectValue placeholder="Auto-create as new" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="">Auto-create as new ledger</SelectItem>
                                    {availableLedgers.map((l) => (
                                      <SelectItem key={l.id} value={l.id}>
                                        {l.name} ({l.type})
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              ) : (
                                <span className="text-xs text-muted-foreground">
                                  {rule.target_name || "Auto-create as new party"}
                                </span>
                              )}
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs">
                              {(rule.confidence * 100).toFixed(0)}%
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>

                {/* Vouchers Preview Table */}
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" /> Parsed Vouchers Preview (First 20)
                  </h3>
                  <div className="rounded-lg border border-border overflow-hidden max-h-64 overflow-y-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-12">#</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Voucher No</TableHead>
                          <TableHead>Date</TableHead>
                          <TableHead>Party / Particulars</TableHead>
                          <TableHead className="text-right">Amount</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {previewData.rows.slice(0, 20).map((r) => (
                          <TableRow key={r.row_number} className={r.is_duplicate ? "bg-amber-500/5" : ""}>
                            <TableCell className="text-xs text-muted-foreground">{r.row_number}</TableCell>
                            <TableCell>
                              <Badge variant="outline">{r.voucher_type}</Badge>
                            </TableCell>
                            <TableCell className="font-mono text-xs">{r.voucher_number}</TableCell>
                            <TableCell className="text-xs">{r.voucher_date}</TableCell>
                            <TableCell className="text-xs">{r.party_name || "—"}</TableCell>
                            <TableCell className="text-right font-medium text-xs">
                              ₹{Number(r.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant={
                                  r.status === "VALID"
                                    ? "success"
                                    : r.status === "DUPLICATE"
                                    ? "warning"
                                    : "destructive"
                                }
                              >
                                {r.status}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>

                {/* Commit Action Panel */}
                <div className="pt-4 border-t border-border flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex-1 max-w-sm">
                    <Label className="text-xs">Save Mappings as Template (Optional)</Label>
                    <Input
                      placeholder="e.g. Standard Tally Prime COA"
                      value={saveTemplateName}
                      onChange={(e) => setSaveTemplateName(e.target.value)}
                      className="h-9 mt-1"
                    />
                  </div>

                  <div className="flex items-center gap-3">
                    <Button variant="outline" onClick={() => setPreviewData(null)}>
                      Cancel
                    </Button>
                    <PermissionGate permission="ACCOUNTING_IMPORT">
                      <Button
                        onClick={handleCommit}
                        disabled={isCommitting || previewData.valid_records === 0}
                        className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white"
                      >
                        {isCommitting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                        Commit {previewData.valid_records} Vouchers to Accounting
                      </Button>
                    </PermissionGate>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Step 3: Post-Commit Reconciliation Report */}
          {commitResult && (
            <Card className="border-emerald-500/40 bg-emerald-500/5">
              <CardHeader>
                <CardTitle className="text-lg flex items-center justify-between text-emerald-800 dark:text-emerald-300">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-6 w-6 text-emerald-600" /> 3. Post-Import Reconciliation Scorecard
                  </div>
                  <Badge
                    variant={commitResult.reconciliation.overall_matched ? "success" : "warning"}
                    className="text-sm px-3 py-1"
                  >
                    {commitResult.reconciliation.overall_matched ? "OVERALL MATCHED 100%" : "DISCREPANCIES DETECTED"}
                  </Badge>
                </CardTitle>
                <CardDescription>
                  Source Tally records compared against atomically committed accounting entries.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="rounded-lg border border-border bg-card overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Entity Type</TableHead>
                        <TableHead className="text-right">Source Count</TableHead>
                        <TableHead className="text-right">Committed Count</TableHead>
                        <TableHead className="text-right">Source Amount (₹)</TableHead>
                        <TableHead className="text-right">Committed Amount (₹)</TableHead>
                        <TableHead className="text-right">Difference</TableHead>
                        <TableHead className="text-center">Audit Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {commitResult.reconciliation.items.map((item, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-semibold">{item.entity_type}</TableCell>
                          <TableCell className="text-right">{item.source_count}</TableCell>
                          <TableCell className="text-right">{item.imported_count}</TableCell>
                          <TableCell className="text-right font-mono">
                            {Number(item.source_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {Number(item.imported_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </TableCell>
                          <TableCell
                            className={`text-right font-mono ${
                              Number(item.difference_amount) !== 0 ? "text-rose-600 font-bold" : "text-emerald-600"
                            }`}
                          >
                            {Number(item.difference_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge variant={item.status === "MATCHED" ? "success" : "warning"}>{item.status}</Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <p className="text-xs text-muted-foreground">
                    Job ID: <code className="font-mono">{commitResult.job_id}</code> | Successfully committed:{" "}
                    <strong>{commitResult.successful_rows}</strong> records.
                  </p>
                  <div className="flex gap-2">
                    <Button variant="outline" asChild>
                      <Link to="/accounting/sales-invoices">View Sales Invoices</Link>
                    </Button>
                    <Button variant="outline" asChild>
                      <Link to="/accounting/ledgers">View Ledgers</Link>
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* TAB 2: EXPORT STUDIO */}
        <TabsContent value="export" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Download className="h-5 w-5 text-primary" /> Tally Export Studio
              </CardTitle>
              <CardDescription>
                Export sales, purchases, payments, receipts, and journals into Tally Prime/ERP 9 compliant XML envelope,
                Daybook CSV, or Multi-sheet Excel workbook.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label className="text-xs">Export Format</Label>
                  <Select value={exportFormat} onValueChange={(val: "XML" | "CSV" | "XLSX") => setExportFormat(val)}>
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="XML">Tally XML (&lt;ENVELOPE&gt; Format)</SelectItem>
                      <SelectItem value="CSV">Daybook CSV</SelectItem>
                      <SelectItem value="XLSX">Multi-Sheet Excel Workbook</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-xs">Financial Year</Label>
                  <Select value={exportFyId} onValueChange={setExportFyId}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="All Financial Years" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Financial Years</SelectItem>
                      {financialYears?.items?.map((fy: FinancialYear) => (
                        <SelectItem key={fy.id} value={fy.id}>
                          {fy.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">From Date</Label>
                    <Input
                      type="date"
                      value={exportStartDate}
                      onChange={(e) => setExportStartDate(e.target.value)}
                      className="mt-1 text-xs"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">To Date</Label>
                    <Input
                      type="date"
                      value={exportEndDate}
                      onChange={(e) => setExportEndDate(e.target.value)}
                      className="mt-1 text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Voucher Types Selection */}
              <div className="space-y-2">
                <Label className="text-xs">Include Voucher Types</Label>
                <div className="flex flex-wrap gap-2">
                  {["SALES", "PURCHASE", "RECEIPT", "PAYMENT", "JOURNAL"].map((t) => {
                    const active = selectedVoucherTypes.includes(t);
                    return (
                      <Badge
                        key={t}
                        variant={active ? "default" : "outline"}
                        className="cursor-pointer px-3 py-1 text-xs"
                        onClick={() => {
                          if (active) {
                            setSelectedVoucherTypes(selectedVoucherTypes.filter((v) => v !== t));
                          } else {
                            setSelectedVoucherTypes([...selectedVoucherTypes, t]);
                          }
                        }}
                      >
                        {t}
                      </Badge>
                    );
                  })}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3 pt-2">
                <Button variant="outline" onClick={handlePreviewExport} disabled={isPreviewingExport} className="gap-2">
                  {isPreviewingExport ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  Preview Export Scope
                </Button>
                <Button onClick={handleDownloadExport} disabled={isExporting} className="gap-2">
                  {isExporting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                  Generate & Download {exportFormat}
                </Button>
              </div>

              {/* Export Preview Scorecard */}
              {exportPreview && (
                <div className="rounded-xl border border-border bg-card p-4 space-y-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Export Profile Scope Preview
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground">Total Vouchers</p>
                      <p className="text-xl font-bold text-foreground mt-0.5">{exportPreview.total_vouchers}</p>
                    </div>
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground">Total Turnover</p>
                      <p className="text-xl font-bold text-foreground mt-0.5 font-mono">
                        ₹{Number(exportPreview.total_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground">Chart Ledgers</p>
                      <p className="text-xl font-bold text-foreground mt-0.5">{exportPreview.ledgers_count}</p>
                    </div>
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground">Parties Exported</p>
                      <p className="text-xl font-bold text-foreground mt-0.5">{exportPreview.parties_count}</p>
                    </div>
                  </div>

                  {exportPreview.voucher_breakdown && (
                    <div className="flex flex-wrap gap-3 pt-2 border-t border-border">
                      {Object.entries(exportPreview.voucher_breakdown).map(([k, v]) => (
                        <div key={k} className="text-xs text-muted-foreground">
                          <span className="font-semibold text-foreground">{k}:</span> {v}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: MAPPING TEMPLATES */}
        <TabsContent value="templates" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-primary" /> Saved Tally Mapping Templates
                </div>
                <Badge variant="outline">{templates.length} Active Profiles</Badge>
              </CardTitle>
              <CardDescription>
                Reusable ledger, tax, and party mapping templates automatically applied during future imports.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingTemplates ? (
                <div className="space-y-2">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : templates.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground space-y-2">
                  <BookOpen className="h-8 w-8 mx-auto text-muted-foreground/60" />
                  <p className="font-medium">No saved mapping templates yet</p>
                  <p className="text-xs">
                    Templates are saved automatically when committing imports with a template name.
                  </p>
                </div>
              ) : (
                <div className="rounded-lg border border-border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Template Name</TableHead>
                        <TableHead>Source Version</TableHead>
                        <TableHead className="text-right">Rules Count</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {templates.map((tpl) => (
                        <TableRow key={tpl.id}>
                          <TableCell className="font-semibold text-foreground">
                            {tpl.name}
                            {tpl.description && (
                              <span className="text-xs text-muted-foreground block">{tpl.description}</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{tpl.source_version || "Tally Prime"}</Badge>
                          </TableCell>
                          <TableCell className="text-right font-medium">{tpl.rules?.length || 0}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {new Date(tpl.created_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteTemplate(tpl.id)}
                              className="text-destructive hover:bg-destructive/10 h-8 w-8 p-0"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
