import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Landmark, Plus, Trash2 } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import { useCapitalGains, useCreateCapitalGain, useDeleteCapitalGain } from "@/hooks/useIncomeTaxCapitalGains";
import { PermissionGate } from "@/components/PermissionGate";
import { Badge } from "@/components/ui/badge";
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
import type { CapitalAssetType, CapitalGainType } from "@/types/incomeTax";

const ASSET_TYPES: CapitalAssetType[] = ["EQUITY_SHARES", "MUTUAL_FUND", "IMMOVABLE_PROPERTY", "GOLD_JEWELLERY", "DEBT_INSTRUMENT", "OTHER"];

const schema = z.object({
  asset_type: z.string().min(1),
  asset_description: z.string().min(1, "Description is required"),
  purchase_date: z.string().min(1, "Purchase date is required"),
  sale_date: z.string().min(1, "Sale date is required"),
  purchase_cost: z.string().optional(),
  transfer_expenses: z.string().optional(),
  sale_consideration: z.string().min(1),
  gain_type: z.string().min(1),
});
type FormValues = z.infer<typeof schema>;

export default function CapitalGainsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id;

  const { data: financialYears } = useFinancialYears(companyId);
  const [fyId, setFyId] = useState<string>("");
  const effectiveFyId = fyId || financialYears?.items.find((fy) => fy.is_current)?.id || "";

  const { data, isLoading } = useCapitalGains(companyId, effectiveFyId || undefined);
  const createMutation = useCreateCapitalGain(companyId ?? "");
  const deleteMutation = useDeleteCapitalGain(companyId ?? "");
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const { register, control, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { asset_type: "EQUITY_SHARES", gain_type: "LONG_TERM" },
  });

  if (!activeCompany || !companyId) return <EmptyCompanyState icon={Landmark} />;

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({
        financial_year_id: effectiveFyId,
        ...values,
        asset_type: values.asset_type as CapitalAssetType,
        gain_type: values.gain_type as CapitalGainType,
      });
      toast({ title: "Capital gain recorded", variant: "success" });
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
          <h1 className="text-2xl font-semibold tracking-tight">Capital Gains</h1>
          <p className="text-sm text-muted-foreground">
            Short/long-term classification is always chosen by the preparer — never derived automatically.
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
                <TableHead>Asset</TableHead>
                <TableHead>Sale Date</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Gain</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((g) => (
                <TableRow key={g.id}>
                  <TableCell>
                    <p className="font-medium">{g.asset_description}</p>
                    <p className="text-xs text-muted-foreground">{g.asset_type.replaceAll("_", " ")}</p>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{g.sale_date}</TableCell>
                  <TableCell><Badge variant="outline">{g.gain_type.replaceAll("_", " ")}</Badge></TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(g.gain_amount)}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => deleteMutation.mutate(g.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Landmark} title="No capital gains recorded" />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) setServerError(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Add capital gain</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            {serverError && <p className="text-xs text-destructive">{serverError}</p>}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Asset type</Label>
                <Controller control={control} name="asset_type" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{ASSET_TYPES.map((t) => <SelectItem key={t} value={t}>{t.replaceAll("_", " ")}</SelectItem>)}</SelectContent>
                  </Select>
                )} />
              </div>
              <div className="space-y-1.5">
                <Label>Gain type</Label>
                <Controller control={control} name="gain_type" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="SHORT_TERM">Short Term</SelectItem>
                      <SelectItem value="LONG_TERM">Long Term</SelectItem>
                    </SelectContent>
                  </Select>
                )} />
              </div>
            </div>
            <div className="space-y-1.5"><Label>Description</Label><Input {...register("asset_description")} /></div>
            {errors.asset_description && <p className="text-xs text-destructive">{errors.asset_description.message}</p>}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Purchase date</Label><Input type="date" {...register("purchase_date")} /></div>
              <div className="space-y-1.5"><Label>Sale date</Label><Input type="date" {...register("sale_date")} /></div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5"><Label>Purchase cost</Label><Input type="number" step="0.01" {...register("purchase_cost")} /></div>
              <div className="space-y-1.5"><Label>Sale value</Label><Input type="number" step="0.01" {...register("sale_consideration")} /></div>
              <div className="space-y-1.5"><Label>Transfer expenses</Label><Input type="number" step="0.01" {...register("transfer_expenses")} /></div>
            </div>
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
