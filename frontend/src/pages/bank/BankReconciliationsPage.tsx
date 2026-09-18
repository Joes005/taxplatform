import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, ScrollText } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useBankAccounts } from "@/hooks/useBankAccounts";
import { useBankReconciliations, useStartBankReconciliation } from "@/hooks/useBankReconciliations";
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
import type { BankReconciliationStatus } from "@/types/bank";

const STATUS_VARIANT: Record<BankReconciliationStatus, "secondary" | "warning" | "success" | "outline"> = {
  OPEN: "secondary",
  IN_PROGRESS: "warning",
  PENDING_REVIEW: "warning",
  RECONCILED: "success",
  LOCKED: "success",
  CANCELLED: "outline",
};

const schema = z.object({
  bank_account_id: z.string().min(1, "Select a bank account"),
  period_start: z.string().min(1, "Start date is required"),
  period_end: z.string().min(1, "End date is required"),
  opening_balance: z.string().min(1, "Opening balance is required"),
  closing_balance: z.string().min(1, "Closing balance is required"),
});
type FormValues = z.infer<typeof schema>;

export default function BankReconciliationsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";
  const { data, isLoading } = useBankReconciliations(companyId);
  const { data: accounts } = useBankAccounts(companyId);
  const startMutation = useStartBankReconciliation(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!activeCompany) return <EmptyCompanyState icon={ScrollText} />;

  const accountName = (id: string) => accounts?.items.find((a) => a.id === id)?.account_name ?? id.slice(0, 8);

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await startMutation.mutateAsync(values);
      toast({ title: "Reconciliation session started", variant: "success" });
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
          <h1 className="text-2xl font-semibold tracking-tight">Reconciliation Sessions</h1>
          <p className="text-sm text-muted-foreground">Start a session per account/period, then run matching.</p>
        </div>
        <PermissionGate permission="BANK_RECONCILE_RUN">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> Start Reconciliation
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
                <TableHead>Account</TableHead>
                <TableHead>Period</TableHead>
                <TableHead className="text-right">Closing Balance</TableHead>
                <TableHead className="text-right">Difference</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">
                    <Link to={`/bank/reconciliations/${r.id}`} className="text-primary hover:underline">
                      {accountName(r.bank_account_id)}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{r.period_start} to {r.period_end}</TableCell>
                  <TableCell className="text-right">{formatMoney(r.closing_balance)}</TableCell>
                  <TableCell className="text-right">{r.difference ? formatMoney(r.difference) : "—"}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[r.status]}>{r.status}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={ScrollText} title="No reconciliation sessions yet" hint="Start one for a bank account and period." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Start reconciliation</DialogTitle>
            <DialogDescription>Enter the period's opening/closing balance as printed on the bank statement.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label htmlFor="recon-account">Bank account</Label>
              <Controller
                control={control}
                name="bank_account_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="recon-account"><SelectValue placeholder="Select bank account" /></SelectTrigger>
                    <SelectContent>
                      {(accounts?.items ?? []).map((a) => <SelectItem key={a.id} value={a.id}>{a.account_name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.bank_account_id && <p className="text-xs text-destructive">{errors.bank_account_id.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="recon-start">Period start</Label>
                <Input id="recon-start" type="date" {...register("period_start")} />
                {errors.period_start && <p className="text-xs text-destructive">{errors.period_start.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="recon-end">Period end</Label>
                <Input id="recon-end" type="date" {...register("period_end")} />
                {errors.period_end && <p className="text-xs text-destructive">{errors.period_end.message}</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="recon-opening">Opening balance</Label>
                <Input id="recon-opening" type="number" step="0.01" {...register("opening_balance")} />
                {errors.opening_balance && <p className="text-xs text-destructive">{errors.opening_balance.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="recon-closing">Closing balance</Label>
                <Input id="recon-closing" type="number" step="0.01" {...register("closing_balance")} />
                {errors.closing_balance && <p className="text-xs text-destructive">{errors.closing_balance.message}</p>}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Starting…" : "Start"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
