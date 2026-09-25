import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Landmark, Plus, Trash2 } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import { useCreateDeduction, useDeductions, useDeleteDeduction } from "@/hooks/useIncomeTaxDeductions";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ApiError } from "@/lib/api-client";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";

const schema = z.object({
  section_code: z.string().min(1, "Section code is required"),
  description: z.string().optional(),
  claimed_amount: z.string().min(1),
});
type FormValues = z.infer<typeof schema>;

export default function DeductionsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id;

  const { data: financialYears } = useFinancialYears(companyId);
  const [fyId, setFyId] = useState<string>("");
  const effectiveFyId = fyId || financialYears?.items.find((fy) => fy.is_current)?.id || "";

  const { data, isLoading } = useDeductions(companyId, effectiveFyId || undefined);
  const createMutation = useCreateDeduction(companyId ?? "");
  const deleteMutation = useDeleteDeduction(companyId ?? "");
  const [open, setOpen] = useState(false);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  if (!activeCompany || !companyId) return <EmptyCompanyState icon={Landmark} />;

  const onSubmit = async (values: FormValues) => {
    try {
      await createMutation.mutateAsync({ financial_year_id: effectiveFyId, ...values });
      toast({ title: "Deduction recorded", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      toast({ title: "Failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Deductions</h1>
          <p className="text-sm text-muted-foreground">
            Eligibility (regime, section cap) is applied when the tax computation runs — the claimed amount is
            never used directly.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={effectiveFyId} onValueChange={setFyId}>
            <SelectTrigger className="w-48"><SelectValue placeholder="Financial year" /></SelectTrigger>
            <SelectContent>
              {(financialYears?.items ?? []).map((fy) => <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <PermissionGate permission="INCOME_TAX_CREATE">
            <Button size="sm" disabled={!effectiveFyId} onClick={() => setOpen(true)}>
              <Plus className="mr-1.5 h-3.5 w-3.5" /> Add
            </Button>
          </PermissionGate>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {!effectiveFyId ? (
          <p className="p-6 text-sm text-muted-foreground">Select a financial year to continue.</p>
        ) : isLoading ? (
          <div className="p-6"><Skeleton className="h-10 w-full" /></div>
        ) : (data ?? []).length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Section</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Claimed</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="font-medium">{d.section_code}</TableCell>
                  <TableCell className="text-muted-foreground">{d.description ?? "—"}</TableCell>
                  <TableCell className="text-right">{formatMoney(d.claimed_amount)}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => deleteMutation.mutate(d.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Landmark} title="No deductions recorded" />
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add deduction</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div className="space-y-1.5">
              <Label>Section code</Label>
              <Input placeholder="80C, 80D, 80G, …" {...register("section_code")} />
              {errors.section_code && <p className="text-xs text-destructive">{errors.section_code.message}</p>}
            </div>
            <div className="space-y-1.5"><Label>Description</Label><Input {...register("description")} /></div>
            <div className="space-y-1.5"><Label>Claimed amount</Label><Input type="number" step="0.01" {...register("claimed_amount")} /></div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
