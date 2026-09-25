import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Landmark, Plus } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useLedgers } from "@/hooks/useAccounting";
import { useBankAccounts, useCreateBankAccount } from "@/hooks/useBankAccounts";
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
import type { BankAccountType } from "@/types/bank";

const accountTypes: BankAccountType[] = ["SAVINGS", "CURRENT", "CASH_CREDIT", "OVERDRAFT", "OTHER"];

const schema = z.object({
  bank_name: z.string().min(1, "Bank name is required").max(255),
  account_name: z.string().min(1, "Account name is required").max(255),
  account_number_masked: z.string().min(1, "Enter a masked account number, e.g. XXXXXX1234").max(30),
  account_type: z.enum(accountTypes as [BankAccountType, ...BankAccountType[]]),
  ifsc_code: z.string().max(11).optional().or(z.literal("")),
  opening_balance: z.string().min(1, "Opening balance is required"),
  opening_balance_date: z.string().min(1, "Date is required"),
  ledger_id: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function BankAccountsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";
  const { data, isLoading } = useBankAccounts(companyId);
  const { data: ledgers } = useLedgers(companyId);
  const createMutation = useCreateBankAccount(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { account_type: "CURRENT" } });

  if (!activeCompany) return <EmptyCompanyState icon={Landmark} />;

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({
        ...values,
        ifsc_code: values.ifsc_code || null,
        ledger_id: values.ledger_id || null,
      });
      toast({ title: "Bank account created", variant: "success" });
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
          <h1 className="text-2xl font-semibold tracking-tight">Bank Accounts</h1>
          <p className="text-sm text-muted-foreground">Only a masked account number is ever stored.</p>
        </div>
        <PermissionGate permission="BANK_CREATE">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New Bank Account
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
                <TableHead>Bank</TableHead>
                <TableHead>Number</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Opening Balance</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium">{a.account_name}</TableCell>
                  <TableCell className="text-muted-foreground">{a.bank_name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{a.account_number_masked}</TableCell>
                  <TableCell className="text-muted-foreground">{a.account_type}</TableCell>
                  <TableCell className="text-right">{formatMoney(a.opening_balance)}</TableCell>
                  <TableCell><Badge variant={a.is_active ? "success" : "secondary"}>{a.is_active ? "Active" : "Inactive"}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Landmark} title="No bank accounts yet" hint="Add a bank account to start importing statements." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New bank account</DialogTitle>
            <DialogDescription>Enter only a masked account number — the full number is never collected.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ba-bank">Bank name</Label>
                <Input id="ba-bank" {...register("bank_name")} />
                {errors.bank_name && <p className="text-xs text-destructive">{errors.bank_name.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ba-account-name">Account name</Label>
                <Input id="ba-account-name" {...register("account_name")} />
                {errors.account_name && <p className="text-xs text-destructive">{errors.account_name.message}</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ba-number">Masked account number</Label>
                <Input id="ba-number" placeholder="XXXXXX1234" {...register("account_number_masked")} />
                {errors.account_number_masked && <p className="text-xs text-destructive">{errors.account_number_masked.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ba-type">Account type</Label>
                <Controller
                  control={control}
                  name="account_type"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger id="ba-type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {accountTypes.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ba-balance">Opening balance</Label>
                <Input id="ba-balance" type="number" step="0.01" {...register("opening_balance")} />
                {errors.opening_balance && <p className="text-xs text-destructive">{errors.opening_balance.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ba-date">Opening balance date</Label>
                <Input id="ba-date" type="date" {...register("opening_balance_date")} />
                {errors.opening_balance_date && <p className="text-xs text-destructive">{errors.opening_balance_date.message}</p>}
              </div>
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="ba-ledger">Linked ledger (optional)</Label>
                <Link to="/accounting/ledgers" className="text-xs text-primary hover:underline">
                  Manage Ledgers
                </Link>
              </div>
              <Controller
                control={control}
                name="ledger_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="ba-ledger"><SelectValue placeholder="No ledger linked" /></SelectTrigger>
                    <SelectContent>
                      {(ledgers?.items ?? []).map((l) => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              />
              <p className="text-xs text-muted-foreground">
                Tip: Link to a Bank ledger (e.g. &quot;Bank Account&quot;) to enable automated book balance comparison.
              </p>
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
