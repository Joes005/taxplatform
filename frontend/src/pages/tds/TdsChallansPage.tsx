import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Receipt, Wallet } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import { useAllocateTdsChallan, useCreateTdsChallan, useTdsChallans, useUpdateTdsChallanStatus } from "@/hooks/useTdsChallans";
import { useTdsTransactions } from "@/hooks/useTdsTransactions";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError } from "@/lib/api-client";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { TDSChallan, TDSChallanStatus } from "@/types/tds";

const STATUS_VARIANT: Record<TDSChallanStatus, "secondary" | "warning" | "success" | "outline"> = {
  DRAFT: "secondary",
  GENERATED: "warning",
  PAID: "success",
  RECONCILED: "success",
  CANCELLED: "outline",
};

const NEXT_STATUS: Partial<Record<TDSChallanStatus, TDSChallanStatus>> = {
  DRAFT: "GENERATED",
  GENERATED: "PAID",
};

const challanSchema = z.object({
  challan_number: z.string().min(1, "Challan number is required"),
  challan_date: z.string().min(1, "Date is required"),
  amount: z.string().min(1, "Amount is required"),
  financial_year_id: z.string().min(1, "Select a financial year"),
});
type ChallanFormValues = z.infer<typeof challanSchema>;

const allocateSchema = z.object({
  tds_transaction_id: z.string().min(1, "Select a transaction"),
  allocated_amount: z.string().min(1, "Amount is required"),
});
type AllocateFormValues = z.infer<typeof allocateSchema>;

export default function TdsChallansPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";

  const { data, isLoading } = useTdsChallans(companyId);
  const { data: financialYears } = useFinancialYears(companyId);
  const { data: deductedTxns } = useTdsTransactions(companyId, 1, "DEDUCTED");
  const createMutation = useCreateTdsChallan(companyId);
  const updateStatusMutation = useUpdateTdsChallanStatus(companyId);
  const allocateMutation = useAllocateTdsChallan(companyId);

  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [allocateTarget, setAllocateTarget] = useState<TDSChallan | null>(null);
  const [allocateError, setAllocateError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ChallanFormValues>({ resolver: zodResolver(challanSchema) });

  const {
    register: registerAllocate,
    control: controlAllocate,
    handleSubmit: handleAllocateSubmit,
    reset: resetAllocate,
    formState: { errors: allocateErrors, isSubmitting: isAllocating },
  } = useForm<AllocateFormValues>({ resolver: zodResolver(allocateSchema) });

  if (!activeCompany) return <EmptyCompanyState icon={Wallet} />;

  const onSubmit = async (values: ChallanFormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync(values);
      toast({ title: "Challan created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  const onAllocate = async (values: AllocateFormValues) => {
    if (!allocateTarget) return;
    setAllocateError(null);
    try {
      await allocateMutation.mutateAsync({
        challanId: allocateTarget.id,
        transactionId: values.tds_transaction_id,
        amount: values.allocated_amount,
      });
      toast({ title: "Challan allocated", variant: "success" });
      setAllocateTarget(null);
      resetAllocate();
    } catch (err) {
      setAllocateError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  const advanceStatus = async (challan: TDSChallan) => {
    const next = NEXT_STATUS[challan.status];
    if (!next) return;
    try {
      await updateStatusMutation.mutateAsync({ id: challan.id, status: next });
      toast({ title: `Challan moved to ${next}`, variant: "success" });
    } catch (err) {
      toast({
        title: "Could not update challan",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">TDS Challans</h1>
          <p className="text-sm text-muted-foreground">
            Tracking/preparation only — this platform never pays a challan or talks to a payment gateway.
          </p>
        </div>
        <PermissionGate permission="TDS_CHALLAN_CREATE">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New Challan
          </Button>
        </PermissionGate>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Challan #</TableHead>
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead className="text-right">Allocated</TableHead>
                <TableHead className="text-right">Unallocated</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium">{c.challan_number}</TableCell>
                  <TableCell className="text-muted-foreground">{c.challan_date}</TableCell>
                  <TableCell className="text-right">{formatMoney(c.amount)}</TableCell>
                  <TableCell className="text-right">{formatMoney(c.allocated_amount)}</TableCell>
                  <TableCell className="text-right">{formatMoney(c.unallocated_amount)}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[c.status]}>{c.status}</Badge></TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1.5">
                      <PermissionGate permission="TDS_CHALLAN_UPDATE">
                        <Button size="sm" variant="outline" onClick={() => { setAllocateTarget(c); resetAllocate(); setAllocateError(null); }}>
                          Allocate
                        </Button>
                      </PermissionGate>
                      {NEXT_STATUS[c.status] && (
                        <PermissionGate permission="TDS_CHALLAN_UPDATE">
                          <Button size="sm" onClick={() => advanceStatus(c)}>
                            Mark {NEXT_STATUS[c.status]}
                          </Button>
                        </PermissionGate>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Receipt} title="No challans yet" hint="Record a challan you've already paid, then allocate it to deducted transactions." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New TDS challan</DialogTitle>
            <DialogDescription>Record a challan you've already paid — this does not submit any payment.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label htmlFor="ch-number">Challan number</Label>
              <Input id="ch-number" {...register("challan_number")} />
              {errors.challan_number && <p className="text-xs text-destructive">{errors.challan_number.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ch-date">Date</Label>
                <Input id="ch-date" type="date" {...register("challan_date")} />
                {errors.challan_date && <p className="text-xs text-destructive">{errors.challan_date.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ch-amount">Amount</Label>
                <Input id="ch-amount" type="number" step="0.01" {...register("amount")} />
                {errors.amount && <p className="text-xs text-destructive">{errors.amount.message}</p>}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ch-fy">Financial year</Label>
              <Controller
                control={control}
                name="financial_year_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="ch-fy"><SelectValue placeholder="Select financial year" /></SelectTrigger>
                    <SelectContent>
                      {(financialYears?.items ?? []).map((fy) => (
                        <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.financial_year_id && <p className="text-xs text-destructive">{errors.financial_year_id.message}</p>}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Creating…" : "Create"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!allocateTarget} onOpenChange={(o) => { if (!o) setAllocateTarget(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Allocate challan {allocateTarget?.challan_number}</DialogTitle>
            <DialogDescription>
              Remaining balance: {allocateTarget ? formatMoney(allocateTarget.unallocated_amount) : ""}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAllocateSubmit(onAllocate)} className="space-y-4">
            {allocateError && <Alert variant="destructive"><AlertDescription>{allocateError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label htmlFor="alloc-txn">TDS transaction (DEDUCTED)</Label>
              <Controller
                control={controlAllocate}
                name="tds_transaction_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="alloc-txn"><SelectValue placeholder="Select transaction" /></SelectTrigger>
                    <SelectContent>
                      {(deductedTxns?.items ?? []).map((t) => (
                        <SelectItem key={t.id} value={t.id}>
                          {t.transaction_date} — {formatMoney(t.tds_amount)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {allocateErrors.tds_transaction_id && (
                <p className="text-xs text-destructive">{allocateErrors.tds_transaction_id.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="alloc-amount">Allocated amount</Label>
              <Input id="alloc-amount" type="number" step="0.01" {...registerAllocate("allocated_amount")} />
              {allocateErrors.allocated_amount && (
                <p className="text-xs text-destructive">{allocateErrors.allocated_amount.message}</p>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAllocateTarget(null)}>Cancel</Button>
              <Button type="submit" disabled={isAllocating}>{isAllocating ? "Allocating…" : "Allocate"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
