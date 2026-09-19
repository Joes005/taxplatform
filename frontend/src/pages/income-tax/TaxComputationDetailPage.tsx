import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Receipt } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import {
  useApproveTaxComputation,
  useCalculateTaxComputation,
  useCancelTaxComputation,
  useLockTaxComputation,
  useSubmitTaxComputationForReview,
  useTaxComputation,
} from "@/hooks/useTaxComputations";
import {
  useApproveItrPreparation,
  useCreateItrPreparation,
  useItrPreparations,
  useLockItrPreparation,
  useSubmitItrPreparationForReview,
  useValidateItrPreparation,
} from "@/hooks/useItrPreparations";
import { taxComputationService } from "@/services/taxComputationService";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { formatMoney, triggerBlobDownload } from "@/lib/utils";
import type { TaxComputationStatus, ValidationIssue } from "@/types/incomeTax";

const STATUS_VARIANT: Record<TaxComputationStatus, "secondary" | "warning" | "success" | "outline"> = {
  DRAFT: "outline",
  CALCULATED: "secondary",
  REVIEW_REQUIRED: "warning",
  READY_FOR_REVIEW: "warning",
  APPROVED: "success",
  LOCKED: "success",
  CANCELLED: "outline",
};

const ISSUE_VARIANT: Record<string, "destructive" | "warning" | "outline"> = {
  ERROR: "destructive",
  WARNING: "warning",
  REVIEW_REQUIRED: "outline",
};

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <span className={bold ? "font-semibold" : "text-muted-foreground"}>{label}</span>
      <span className={bold ? "font-semibold" : ""}>{value}</span>
    </div>
  );
}

export default function TaxComputationDetailPage() {
  const { computationId } = useParams<{ computationId: string }>();
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  if (!activeCompany) return <Receipt className="h-6 w-6" />;
  const companyId = activeCompany.company_id;

  const { data: computation, isLoading } = useTaxComputation(companyId, computationId);
  const calculate = useCalculateTaxComputation(companyId, computationId ?? "");
  const submitForReview = useSubmitTaxComputationForReview(companyId, computationId ?? "");
  const approve = useApproveTaxComputation(companyId, computationId ?? "");
  const lock = useLockTaxComputation(companyId, computationId ?? "");
  const cancel = useCancelTaxComputation(companyId, computationId ?? "");

  const { data: preparations } = useItrPreparations(companyId);
  const createItr = useCreateItrPreparation(companyId);
  const preparation = preparations?.items.find((p) => p.tax_computation_id === computationId);

  const [downloading, setDownloading] = useState(false);

  if (isLoading || !computation || !computationId) return <Skeleton className="h-96 w-full" />;

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast({ title: message, variant: "success" });
    } catch (err) {
      toast({ title: "Action failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const download = async (format: "csv" | "xlsx") => {
    setDownloading(true);
    try {
      const { blob, filename } = await taxComputationService.exportComputation(companyId, computationId, format);
      triggerBlobDownload(blob, filename ?? `tax-computation.${format}`);
    } catch (err) {
      toast({ title: "Export failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  };

  const status = computation.status;

  return (
    <div className="space-y-6">
      <Link to="/income-tax/computations" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to computations
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">AY {computation.assessment_year} — {computation.tax_regime.replaceAll("_", " ")}</h1>
          <p className="text-sm text-muted-foreground">An internal preparation, never a filed return.</p>
        </div>
        <Badge variant={STATUS_VARIANT[status]} className="text-sm">{status.replaceAll("_", " ")}</Badge>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-2 pt-6">
          {status === "DRAFT" && (
            <PermissionGate permission="INCOME_TAX_CALCULATE">
              <Button size="sm" onClick={() => run(() => calculate.mutateAsync(), "Computation calculated")}>Calculate</Button>
            </PermissionGate>
          )}
          {(status === "CALCULATED" || status === "REVIEW_REQUIRED") && (
            <PermissionGate permission="INCOME_TAX_CALCULATE">
              <Button size="sm" variant="outline" onClick={() => run(() => calculate.mutateAsync(), "Recalculated")}>Recalculate</Button>
            </PermissionGate>
          )}
          {(status === "CALCULATED" || status === "REVIEW_REQUIRED") && (
            <PermissionGate permission="INCOME_TAX_REVIEW">
              <Button size="sm" onClick={() => run(() => submitForReview.mutateAsync(), "Submitted for review")}>Submit for Review</Button>
            </PermissionGate>
          )}
          {status === "READY_FOR_REVIEW" && (
            <PermissionGate permission="INCOME_TAX_APPROVE">
              <Button size="sm" onClick={() => run(() => approve.mutateAsync(), "Approved")}>Approve</Button>
            </PermissionGate>
          )}
          {status === "APPROVED" && (
            <PermissionGate permission="INCOME_TAX_LOCK">
              <Button size="sm" onClick={() => run(() => lock.mutateAsync(), "Locked")}>Lock</Button>
            </PermissionGate>
          )}
          {["DRAFT", "CALCULATED", "REVIEW_REQUIRED", "READY_FOR_REVIEW"].includes(status) && (
            <PermissionGate permission="INCOME_TAX_UPDATE">
              <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => run(() => cancel.mutateAsync(), "Cancelled")}>
                Cancel
              </Button>
            </PermissionGate>
          )}
          <PermissionGate permission="INCOME_TAX_EXPORT">
            <Button size="sm" variant="outline" disabled={downloading} onClick={() => download("csv")}>
              <Download className="mr-1.5 h-3.5 w-3.5" /> CSV
            </Button>
            <Button size="sm" variant="outline" disabled={downloading} onClick={() => download("xlsx")}>
              <Download className="mr-1.5 h-3.5 w-3.5" /> XLSX
            </Button>
          </PermissionGate>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Computation Breakdown</h2>
          <div className="divide-y divide-border">
            <Row label="Salary Income" value={formatMoney(computation.salary_income)} />
            <Row label="House Property Income" value={formatMoney(computation.house_property_income)} />
            <Row label="Business/Profession Income" value={formatMoney(computation.business_income)} />
            <Row label="Capital Gains" value={formatMoney(computation.capital_gains_income)} />
            <Row label="Other Sources" value={formatMoney(computation.other_income)} />
            <Row label="Gross Total Income" value={formatMoney(computation.gross_total_income)} bold />
            <Row label="Deductions" value={`(${formatMoney(computation.total_deductions)})`} />
            <Row label="Taxable Income" value={formatMoney(computation.taxable_income)} bold />
            <Row label="Tax Before Rebate" value={formatMoney(computation.tax_before_rebate)} />
            <Row label="Rebate" value={`(${formatMoney(computation.rebate)})`} />
            <Row label="Surcharge" value={formatMoney(computation.surcharge)} />
            <Row label="Cess" value={formatMoney(computation.cess)} />
            <Row label="Gross Tax Liability" value={formatMoney(computation.gross_tax_liability)} bold />
            <Row label="TDS Credit" value={`(${formatMoney(computation.tds_credit_total)})`} />
            <Row label="Advance Tax" value={`(${formatMoney(computation.advance_tax_total)})`} />
            <Row label="Self-Assessment Tax" value={`(${formatMoney(computation.self_assessment_tax_total)})`} />
            <Row label="Balance Payable / (Refund)" value={formatMoney(computation.balance_payable_or_refund)} bold />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3 pt-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">ITR Preparation</h2>
          {preparation ? (
            <ItrPreparationSection companyId={companyId} preparationId={preparation.id} />
          ) : (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {status === "DRAFT" ? "Calculate the computation first." : "No ITR preparation created yet."}
              </p>
              <PermissionGate permission="INCOME_TAX_CREATE">
                <Button
                  size="sm"
                  disabled={status === "DRAFT"}
                  onClick={() => run(() => createItr.mutateAsync(computationId), "ITR preparation created")}
                >
                  Create ITR Preparation
                </Button>
              </PermissionGate>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ItrPreparationSection({ companyId, preparationId }: { companyId: string; preparationId: string }) {
  const { toast } = useToast();
  const validateMutation = useValidateItrPreparation(companyId, preparationId);
  const submitMutation = useSubmitItrPreparationForReview(companyId, preparationId);
  const approveMutation = useApproveItrPreparation(companyId, preparationId);
  const lockMutation = useLockItrPreparation(companyId, preparationId);
  const [issues, setIssues] = useState<ValidationIssue[] | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast({ title: message, variant: "success" });
    } catch (err) {
      toast({ title: "Action failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  const validate = async () => {
    try {
      const result = await validateMutation.mutateAsync();
      setIssues(result.issues);
      setStatus(result.preparation.status);
      toast({ title: result.has_errors ? "Validation found errors" : "Validation passed" });
    } catch (err) {
      toast({ title: "Validation failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <PermissionGate permission="INCOME_TAX_VALIDATE">
          <Button size="sm" variant="outline" onClick={validate}>Validate</Button>
        </PermissionGate>
        <PermissionGate permission="INCOME_TAX_REVIEW">
          <Button size="sm" variant="outline" onClick={() => run(() => submitMutation.mutateAsync(), "Submitted for review")}>
            Submit for Review
          </Button>
        </PermissionGate>
        <PermissionGate permission="INCOME_TAX_APPROVE">
          <Button size="sm" onClick={() => run(() => approveMutation.mutateAsync(), "ITR approved")}>Approve</Button>
        </PermissionGate>
        <PermissionGate permission="INCOME_TAX_LOCK">
          <Button size="sm" onClick={() => run(() => lockMutation.mutateAsync(), "ITR locked")}>Lock</Button>
        </PermissionGate>
      </div>
      {status && <Badge variant="outline">{status.replaceAll("_", " ")}</Badge>}
      {issues && (
        <div className="space-y-1.5">
          {issues.length === 0 ? (
            <p className="text-sm text-muted-foreground">No validation issues.</p>
          ) : (
            issues.map((issue, index) => (
              <div key={index} className="flex items-start gap-2 rounded-md border border-border p-2 text-sm">
                <Badge variant={ISSUE_VARIANT[issue.severity] ?? "outline"}>{issue.severity}</Badge>
                <span>{issue.message}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
