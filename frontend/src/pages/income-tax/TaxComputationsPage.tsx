import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Receipt } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import { useCreateTaxComputation, useTaxComputations } from "@/hooks/useTaxComputations";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ApiError } from "@/lib/api-client";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { TaxComputationStatus, TaxRegime } from "@/types/incomeTax";

const STATUS_VARIANT: Record<TaxComputationStatus, "secondary" | "warning" | "success" | "outline"> = {
  DRAFT: "outline",
  CALCULATED: "secondary",
  REVIEW_REQUIRED: "warning",
  READY_FOR_REVIEW: "warning",
  APPROVED: "success",
  LOCKED: "success",
  CANCELLED: "outline",
};

const schema = z.object({
  financial_year_id: z.string().min(1, "Select a financial year"),
  tax_regime: z.string().min(1),
});
type FormValues = z.infer<typeof schema>;

export default function TaxComputationsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  if (!activeCompany) return <EmptyCompanyState icon={Receipt} />;
  const companyId = activeCompany.company_id;

  const { data, isLoading } = useTaxComputations(companyId);
  const { data: financialYears } = useFinancialYears(companyId);
  const createMutation = useCreateTaxComputation(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const { control, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { tax_regime: "NEW_REGIME" },
  });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({ financialYearId: values.financial_year_id, taxRegime: values.tax_regime as TaxRegime });
      toast({ title: "Tax computation created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tax Computations</h1>
          <p className="text-sm text-muted-foreground">One computation per financial year and regime.</p>
        </div>
        <PermissionGate permission="INCOME_TAX_CREATE">
          <Button onClick={() => setOpen(true)}><Plus className="mr-1.5 h-4 w-4" /> New Computation</Button>
        </PermissionGate>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="p-6"><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Assessment Year</TableHead>
                <TableHead>Regime</TableHead>
                <TableHead className="text-right">Taxable Income</TableHead>
                <TableHead className="text-right">Balance</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>
                    <Link to={`/income-tax/computations/${c.id}`} className="font-medium text-primary hover:underline">
                      AY {c.assessment_year}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{c.tax_regime.replaceAll("_", " ")}</TableCell>
                  <TableCell className="text-right">{formatMoney(c.taxable_income)}</TableCell>
                  <TableCell className="text-right">{formatMoney(c.balance_payable_or_refund)}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[c.status]}>{c.status.replaceAll("_", " ")}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Receipt} title="No tax computations yet" hint="Create one for a financial year." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New tax computation</DialogTitle>
            <DialogDescription>Income/deductions/credits are pulled in live when you calculate it.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <p className="text-xs text-destructive">{serverError}</p>}
            <div className="space-y-1.5">
              <Label>Financial year</Label>
              <Controller control={control} name="financial_year_id" render={({ field }) => (
                <Select onValueChange={field.onChange} value={field.value}>
                  <SelectTrigger><SelectValue placeholder="Select financial year" /></SelectTrigger>
                  <SelectContent>
                    {(financialYears?.items ?? []).map((fy) => <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              )} />
              {errors.financial_year_id && <p className="text-xs text-destructive">{errors.financial_year_id.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Tax regime</Label>
              <Controller control={control} name="tax_regime" render={({ field }) => (
                <Select onValueChange={field.onChange} value={field.value}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NEW_REGIME">New Regime</SelectItem>
                    <SelectItem value="OLD_REGIME">Old Regime</SelectItem>
                  </SelectContent>
                </Select>
              )} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Creating…" : "Create"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
