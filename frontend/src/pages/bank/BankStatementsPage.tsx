import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, ScrollText, UploadCloud } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useBankAccounts } from "@/hooks/useBankAccounts";
import { useCreateBankStatement, useBankStatements } from "@/hooks/useBankStatements";
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
import type { BankStatementStatus } from "@/types/bank";

const STATUS_VARIANT: Record<BankStatementStatus, "secondary" | "warning" | "success" | "outline" | "destructive"> = {
  IMPORTED: "secondary",
  PROCESSING: "warning",
  READY: "success",
  RECONCILING: "warning",
  RECONCILED: "success",
  FAILED: "destructive",
  ARCHIVED: "outline",
};

const schema = z.object({
  bank_account_id: z.string().min(1, "Select a bank account"),
  statement_name: z.string().min(1, "Name is required"),
  period_start: z.string().min(1, "Start date is required"),
  period_end: z.string().min(1, "End date is required"),
  opening_balance: z.string().min(1, "Opening balance is required"),
  closing_balance: z.string().min(1, "Closing balance is required"),
});
type FormValues = z.infer<typeof schema>;

export default function BankStatementsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";
  const { data, isLoading } = useBankStatements(companyId);
  const { data: accounts } = useBankAccounts(companyId);
  const createMutation = useCreateBankStatement(companyId);
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
      await createMutation.mutateAsync(values);
      toast({ title: "Statement registered", variant: "success" });
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
          <h1 className="text-2xl font-semibold tracking-tight">Bank Statements</h1>
          <p className="text-sm text-muted-foreground">Register a statement, then import its transactions.</p>
        </div>
        <PermissionGate permission="BANK_STATEMENT_IMPORT">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New Statement
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
                <TableHead>Statement</TableHead>
                <TableHead>Account</TableHead>
                <TableHead>Period</TableHead>
                <TableHead className="text-right">Closing Balance</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.statement_name}</TableCell>
                  <TableCell className="text-muted-foreground">{accountName(s.bank_account_id)}</TableCell>
                  <TableCell className="text-muted-foreground">{s.period_start} to {s.period_end}</TableCell>
                  <TableCell className="text-right">{formatMoney(s.closing_balance)}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[s.status]}>{s.status}</Badge></TableCell>
                  <TableCell className="text-right">
                    {s.status === "PROCESSING" && (
                      <PermissionGate permission="BANK_STATEMENT_IMPORT">
                        <Link to={`/accounting/imports/new?importType=BANK_STATEMENT&bankStatementId=${s.id}`}>
                          <Button size="sm" variant="outline">
                            <UploadCloud className="mr-1.5 h-3.5 w-3.5" /> Import transactions
                          </Button>
                        </Link>
                      </PermissionGate>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={ScrollText} title="No statements yet" hint="Register a statement to start importing transactions." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Register bank statement</DialogTitle>
            <DialogDescription>Enter the opening/closing balance exactly as printed on the statement.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label htmlFor="stmt-account">Bank account</Label>
              <Controller
                control={control}
                name="bank_account_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="stmt-account"><SelectValue placeholder="Select bank account" /></SelectTrigger>
                    <SelectContent>
                      {(accounts?.items ?? []).map((a) => <SelectItem key={a.id} value={a.id}>{a.account_name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.bank_account_id && <p className="text-xs text-destructive">{errors.bank_account_id.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="stmt-name">Statement name</Label>
              <Input id="stmt-name" placeholder="e.g. September 2026" {...register("statement_name")} />
              {errors.statement_name && <p className="text-xs text-destructive">{errors.statement_name.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="stmt-start">Period start</Label>
                <Input id="stmt-start" type="date" {...register("period_start")} />
                {errors.period_start && <p className="text-xs text-destructive">{errors.period_start.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="stmt-end">Period end</Label>
                <Input id="stmt-end" type="date" {...register("period_end")} />
                {errors.period_end && <p className="text-xs text-destructive">{errors.period_end.message}</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="stmt-opening">Opening balance</Label>
                <Input id="stmt-opening" type="number" step="0.01" {...register("opening_balance")} />
                {errors.opening_balance && <p className="text-xs text-destructive">{errors.opening_balance.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="stmt-closing">Closing balance</Label>
                <Input id="stmt-closing" type="number" step="0.01" {...register("closing_balance")} />
                {errors.closing_balance && <p className="text-xs text-destructive">{errors.closing_balance.message}</p>}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Registering…" : "Register"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
